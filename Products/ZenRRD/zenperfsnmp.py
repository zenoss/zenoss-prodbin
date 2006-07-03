#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenperfsnmp

Gets snmp performance data and stores it in the RRD files.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import os
import time
import logging
log = logging.getLogger("zen.zenperfsnmp")

from sets import Set

from twisted.internet import reactor, defer
from twistedsnmp.agentproxy import AgentProxy

import Globals
from Products.ZenUtils.Chain import Chain
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenEvents import Event

from RRDUtil import RRDUtil
from RRDDaemon import RRDDaemon

from FileCleanup import FileCleanup

MAX_OIDS_PER_REQUEST = 40
MAX_SNMP_REQUESTS = 30

def chunk(lst, n):
    'break lst into n-sized chunks'
    return [lst[i:i+n] for i in range(0, len(lst), n)]

try:
    sorted = sorted                     # added in python 2.4
except NameError:
    def sorted(lst, *args, **kw):
        lst.sort(*args, **kw)
        return lst

def firsts(lst):
    'the first element of every item in a sequence'
    return [item[0] for item in lst]


class Status:
    'keep track of the status of many parallel requests'
    _total = _success = _fail = 0
    _startTime = _stopTime = 0.0
    _deferred = None

    
    def start(self, count):
        'start the clock'
        self._total = count
        self._startTime = time.time()
        self._deferred = defer.Deferred()
        self._checkFinished()           # count could be zero
        return self._deferred


    def record(self, successOrFailure):
        'single funtion to record success or failure'
        if successOrFailure:
            self.success()
        else:
            self.fail()

        
    def success(self, *unused):
        'record a successful result'
        self._success += 1
        self._checkFinished()


    def fail(self, *unused):
        'record a failed operation'
        self._fail += 1
        self._checkFinished()


    def _checkFinished(self):
        'determine the stopping point'
        if self.finished():
            self._stopTime = time.time()
            if not self._deferred.called:
                self._deferred.callback(self)


    def finished(self):
        'determine if we have finished everything'
        return self.outstanding() == 0


    def stats(self):
        'provide a summary of the effort'
        stopTime = self._stopTime
        if not self.finished():
            stopTime = time.time()
        return (self._total, self._success, self._fail,
                stopTime - self._startTime)


    def outstanding(self):
        'return the number of unfinished operations'
        return self._total - (self._success + self._fail)


    def moreWork(self, count):
        self._total += count


class SnmpStatus:
    "track and report SNMP status failures"

    snmpStatusEvent = {'eventClass': '/Status/Snmp',
                       'component': 'snmp',
                       'eventGroup': 'SnmpTest'}

    
    def __init__(self, snmpState):
        self.count = snmpState


    def updateStatus(self, deviceName, success, eventCb):
        'Send events on snmp failures'
        if success:
            if self.count > 0:
                summary='snmp agent up on device ' + deviceName
                eventCb(self.snmpStatusEvent, 
                        device=deviceName, summary=summary,
                        severity=Event.Clear)
                log.info(summary)
            self.count = 0
        else:
            summary='snmp agent down on device ' + deviceName
            eventCb(self.snmpStatusEvent,
                    device=deviceName, summary=summary,
                    severity=Event.Warning)
            log.warn(summary)
            self.count += 1


class Threshold:
    'Hold threshold config and send events based on the current value'
    count = 0
    label = ''
    minimum = None
    maximum = None
    severity = Event.Notice
    escalateCount = 0
    threshevt = {'eventClass':'/Perf/Snmp', 'agent': 'ZenPerfSnmp'}


    def __init__(self, label, minimum, maximum, severity, count):
        self.label = label
        self.minimum = minimum
        self.maximum = maximum
        self.severity = severity
        self.escalateCount = count


    def check(self, device, cname, oid, value, eventCb):
        'Check the value for min/max thresholds, and post events'
        thresh = None
        if self.maximum is not None and value >= self.maximum:
            thresh = self.maximum
        if self.minimum is not None and value <= self.minimum:
            thresh = self.maximum
        if thresh is not None:
            self.count += 1
            severity = self.severity
            if self.escalateCount and self.count >= self.escalateCount:
                severity += 1
            summary = '%s %s threshold of %s exceeded: current value %.2f' % (
                device, self.label, thresh, value)
            eventCb(self.threshevt,
                    device=device,
                    summary=summary,
                    eventKey=oid,
                    component=cname,
                    severity=severity)
        else:
            if self.count:
                summary = '%s %s threshold restored current value: %.2f' % (
                    device, self.label, value)
                eventCb(self.threshevt,
                        device=device,
                        summary=summary,
                        eventKey=oid,
                        component=cname,
                        severity=Event.Clear)
            self.count = 0


class OidData:
    def __init__(self, name, path,
                 dataStorageType, rrdCreateCommand, thresholds):
        self.name = name
        self.path = path
        self.dataStorageType = dataStorageType
        self.rrdCreateCommand = rrdCreateCommand
        self.thresholds = thresholds



class zenperfsnmp(RRDDaemon):
    "Periodically query all devices for SNMP values to archive in RRD files"
    
    # these names need to match the property values in StatusMonitorConf
    maxRrdFileAge = 30 * (24*60*60)     # seconds
    status = Status()

    def __init__(self):
        RRDDaemon.__init__(self, 'zenperfsnmp')
        self.proxies = {}
        self.queryWorkList = Set()
        self.unresponsiveDevices = Set()
        self.cycleComplete = False
        self.snmpOidsRequested = 0
        perfRoot = performancePath('')
        if not os.path.exists(perfRoot):
	    os.makedirs(perfRoot)
        self.fileCleanup = FileCleanup(perfRoot, '.*\\.rrd$')
        self.fileCleanup.process = self.cleanup
        self.fileCleanup.start()

    def cleanup(self, fullPath):
        self.log.warning("Deleting old RRD file: %s", fullPath)
        try:
            os.unlink(fullPath)
        except OSError:
            self.log.error("Unable to delete old RRD file: %s", fullPath)

    def buildOptions(self):
        RRDDaemon.buildOptions(self)
        self.parser.add_option('--device', dest='device', default="",
                               help='gather performance for a single device')

    def maybeQuit(self):
        "Stop if all performance has been fetched, and we aren't cycling"
        if self.cycleComplete and \
           not self.options.daemon and \
           not self.options.cycle:
            reactor.stop()


    def startUpdateConfig(self, driver):
        'Periodically ask the Zope server for basic configuration data.'
        
        yield self.model.callRemote('getDevices', self.options.device)
        self.updateDeviceList(driver.next())

        yield self.model.callRemote('propertyItems')
        self.setPropertyItems(driver.next())
        
        yield self.model.callRemote('getDefaultRRDCreateCommand')
        createCommand = driver.next()

        self.rrd = RRDUtil(createCommand, self.snmpCycleInterval)

        driveLater(self.configCycleInterval * 60, self.startUpdateConfig)


    def updateDeviceList(self, deviceList):
        'Update the config for devices devices'
        if self.options.device:
            self.log.debug('Gathering performance data for %s ' %
                           self.options.device)

        if not deviceList:
            self.log.warn("no devices found, keeping existing list")
            return

        self.log.debug('Configured %d devices' % len(deviceList))

        for snmpTargets in deviceList:
            self.updateDeviceConfig(snmpTargets)
            
        # stop collecting those no longer in the list
        deviceNames = Set([d[0][0] for d in deviceList])
        doomed = Set(self.proxies.keys()) - deviceNames
        for name in doomed:
            self.log.debug('removing device %s' % name)
            del self.proxies[name]
            # we could delete the RRD files, too


    def updateAgentProxy(self,
                         deviceName, snmpStatus, ip, port, community,
                         version, timeout, tries):
        "create or update proxy"
        # find any cached proxy
        p = self.proxies.get(deviceName, None)
        if not p:
            p = AgentProxy(ip=ip,
                           port=port,
                           community=community,
                           snmpVersion=version,
                           protocol=self.snmpPort.protocol,
                           allowCache=True)
            p.oidMap = {}
            p.snmpStatus = SnmpStatus(snmpStatus)
            p.singleOidMode = False
        else:
            p.ip = ip
            p.port = port
            p.community = community
            p.snmpVersion = version
        p.timeout = timeout
        p.tries = tries
        return p


    def updateDeviceConfig(self, snmpTargets):
        'Save the device configuration and create an SNMP proxy to talk to it'
        (deviceName, snmpStatus, hostPort, snmpConfig), oidData = snmpTargets
        if not oidData: return
        (ip, port)= hostPort
        (community, version, timeout, tries) = snmpConfig
        self.log.debug("received config for %s", deviceName)
        if version.find('1') >= 0:
            version = '1'
        else:
            version = '2'
        p = self.updateAgentProxy(deviceName, snmpStatus,
                                  ip, port, community,
                                  version, timeout, tries)
	for name, oid, path, dsType, createCmd, thresholds in oidData:
            createCmd = createCmd.strip()
            oid = '.'+oid.lstrip('.')
            thresholds = [Threshold(*t) for t in thresholds]
            p.oidMap[oid] = OidData(name, path, dsType, createCmd, thresholds)
        self.proxies[deviceName] = p


    def scanCycle(self, *unused):
        self.log.debug("getting device ping issues")
        proxy = self.buildProxy(self.options.zem)
        d = proxy.callRemote('getDevicePingIssues')
        d.addBoth(self.setUnresponsiveDevices)
        reactor.callLater(self.snmpCycleInterval, self.scanCycle)


    def setUnresponsiveDevices(self, arg):
        "remember all the unresponsive devices"
        if isinstance(arg, list):
            deviceList = arg
            self.log.debug('Unresponsive devices: %r' % deviceList)
            self.unresponsiveDevices = Set(firsts(deviceList))
        else:
            self.log.error(arg)
        self.readDevices()

        
    def readDevices(self, unused=None):
        'Periodically fetch the performance values from all known devices'
        
        if not self.status.finished():
            _, _, _, age = self.status.stats()
            if age < self.configCycleInterval * 2:
                self.log.warning("There are still %d devices to query, "
                                 "waiting for them to finish" %
                                 self.status.outstanding())
                return
            self.log.warning("Devices status is not clearing.  Restarting.")

        self.queryWorkList =  Set(self.proxies.keys())
        self.queryWorkList -= self.unresponsiveDevices
        self.status = Status()
        d = self.status.start(len(self.queryWorkList))
        d.addCallback(self.reportRate)
        for unused in range(MAX_SNMP_REQUESTS):
            if not self.queryWorkList: break
            self.startReadDevice(self.queryWorkList.pop())


    def reportRate(self, *unused):
        'Finished reading all the devices, report stats and maybe stop'
        total, success, failed, runtime = self.status.stats()
        self.log.info("collected %d of %d devices in %.2f" %
                      (success, total, runtime))
        self.log.debug("Sent %d SNMP OID requests", self.snmpOidsRequested)
        self.snmpOidsRequested = 0
        self.heartbeat()


    def startReadDevice(self, deviceName):
        '''Initiate a request (or several) to read the performance data
        from a device'''
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        # ensure that the request will fit in a packet
        n = MAX_OIDS_PER_REQUEST
        if proxy.singleOidMode:
            n = 1
        def getLater(oids):
            return proxy.get(oids, proxy.timeout, proxy.tries)
        chain = Chain(getLater, iter(chunk(sorted(proxy.oidMap.keys()), n)))
        d = chain.run()
        d.addCallback(self.storeValues, deviceName)
        self.snmpOidsRequested += len(proxy.oidMap)
        return d


    def badOid(self, deviceName, oid):
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        name = proxy.oidMap[oid].name
        summary = 'Error reading value for "%s" on %s (oid %s is bad)' % (
            name, deviceName, oid)
        self.sendEvent(proxy.snmpStatus.snmpStatusEvent,
                       device=deviceName, summary=summary,
                       component=name,
                       severity=Event.Notice)
        self.log.warn(summary)
        del proxy.oidMap[oid]
        

    def storeValues(self, updates, deviceName):
        'decode responses from devices and store the elements in RRD files'

        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return

        # Look for problems
        for success, update in updates:
            # empty update is probably a bad OID in the request somewhere
            if success and not update and not proxy.singleOidMode:
                self.status.record(True)
                proxy.singleOidMode = True
                self.status.moreWork(1)
                self.log.warn('Error collecting data on %s, recollecting',
                              deviceName)
                self.startReadDevice(deviceName)
                return

        successCount = sum(firsts(updates))
        oids = []
        for success, update in updates:
            if success:
                for oid, value in update.items():
                    # should always get something back
                    if value == '':
                        self.badOid(deviceName, oid)
                    else:
                        self.storeRRD(deviceName, oid, value)
                    oids.append(oid)

        if successCount == len(updates) and proxy.singleOidMode:
            # remove any oids that didn't report
            for doomed in Set(proxy.oidMap.keys()) - Set(oids):
                self.badOid(deviceName, doomed)

        if self.queryWorkList:
            self.startReadDevice(self.queryWorkList.pop())

        if successCount:
            successPercent = successCount * 100 / len(updates)
            if successPercent not in (0, 100):
                self.log.debug("Successful request ratio for %s is %2d%%",
                               deviceName,
                               successPercent)
        success = True
        if updates:
            success = successCount > 0
        self.status.record(success)
        proxy.snmpStatus.updateStatus(deviceName, success, self.sendEvent)


    def storeRRD(self, device, oid, value):
        'store a value into an RRD file'
        oidData = self.proxies[device].oidMap[oid]

        value = self.rrd.save(oidData.path[1:],
                              value,
                              oidData.dataStorageType,
                              oidData.rrdCreateCommand)

        for threshold in oidData.thresholds:
            threshold.check(device, oidData.name, oid, value, self.sendEvent)


    def main(self):
        "Run forever, fetching and storing"

        self.sendEvent(self.startevt)
        drive(zpf.startUpdateConfig).addCallbacks(self.scanCycle, self.error)
        reactor.run(installSignalHandlers=False)
        self.sendEvent(self.stopevt, now=True)


if __name__ == '__main__':
    zpf = zenperfsnmp()
    zpf.main()
