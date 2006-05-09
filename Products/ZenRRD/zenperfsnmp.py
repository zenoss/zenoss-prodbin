#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenperfsnmp

Gets snmp performance data and stores it in the RRD files.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import os
import socket
import time
import logging
log = logging.getLogger("zen.zenperfsnmp")

from sets import Set

import Globals

from twisted.internet import reactor, defer

from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.TwistedAuth import AuthProxy
from Products.ZenModel.PerformanceConf import performancePath

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp import snmpprotocol

import CountedProxy

BASE_URL = 'http://localhost:8080/zport/dmd'
DEFAULT_URL = BASE_URL + '/Monitors/StatusMonitors/localhost'
MAX_OIDS_PER_REQUEST = 200
MAX_SNMP_REQUESTS = 100
FAILURE_COUNT_INCREASES_SEVERITY = 10

COMMON_EVENT_INFO = {
    'agent': 'zenperfsnmp',
    'manager':socket.getfqdn(),
    }

def chunk(lst, n):
    'break lst into n-sized chunks'
    return [lst[i:i+n] for i in range(0, len(lst), n)]

def rrdPath(branch):
    'compute where the RDD perf files should go'
    return performancePath(branch[1:] + '.rrd')

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
                        severity=0)
                log.info(summary)
            self.count = 0
        else:
            summary='snmp agent down on device ' + deviceName
            eventCb(self.snmpStatusEvent,
                    device=deviceName, summary=summary,
                    severity=4)
            log.warn(summary)
            self.count += 1


class Threshold:
    'Hold threshold config and send events based on the current value'
    count = 0
    label = ''
    minimum = None
    maximum = None
    severity = 3
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
                        severity=0)
            self.count = 0

class OidData:
    def __init__(self, name, path,
                 dataStorageType, rrdCreateCommand, thresholds):
        self.name = name
        self.path = path
        self.dataStorageType = dataStorageType
        self.rrdCreateCommand = rrdCreateCommand
        self.thresholds = thresholds

class zenperfsnmp(ZenDaemon):
    "Periodically query all devices for SNMP values to archive in RRD files"
    
    startevt = {'device':socket.getfqdn(), 'eventClass':'/App/Start', 
                'component':'zenperfsnmp', 'summary': 'started', 'severity': 0}
    stopevt = {'device':socket.getfqdn(), 'eventClass':'/App/Stop', 
                'component':'zenperfsnmp', 'summary': 'stopped', 'severity': 4}
    heartbeat = {'device':socket.getfqdn(), 'component':'zenperfsnmp',
                    'eventClass':'/Heartbeat'}

    # these names need to match the property values in StatusMonitorConf
    defaultRRDCreateCommand = None
    configCycleInterval = 20            # minutes
    snmpCycleInterval = 5*60            # seconds
    status = Status()

    def __init__(self):
        ZenDaemon.__init__(self)
        CountedProxy.setCallback(self.maybeQuit)
        self.model = self.buildProxy(self.options.zopeurl)
        self.proxies = {}
        self.snmpPort = snmpprotocol.port()
        self.queryWorkList = Set()
        baseURL = '/'.join(self.options.zopeurl.rstrip('/').split('/')[:-2])
        if not self.options.zem:
            self.options.zem = baseURL + '/ZenEventManager'
        self.zem = self.buildProxy(self.options.zem)
        self.configLoaded = defer.Deferred()
        self.configLoaded.addCallbacks(self.readDevices, self.quit)
        self.unresponsiveDevices = Set()
        self.devicesRead = None


    def buildOptions(self):
        ZenDaemon.buildOptions(self)

        self.parser.add_option('--device', dest='device',
                               help='gather performance for a single device')

        self.parser.add_option(
            "-z", "--zopeurl",
            dest="zopeurl",
            help="XMLRPC url path for performance configuration server",
            default=DEFAULT_URL)
        self.parser.add_option(
            "-u", "--zopeusername",
            dest="zopeusername", help="username for zope server",
            default='admin')
        self.parser.add_option("-p", "--zopepassword", dest="zopepassword")
        self.parser.add_option("--debug", dest="debug", action='store_true'
                                default='False')
        self.parser.add_option(
            '--zem', dest='zem',
            help="XMLRPC path to an ZenEventManager instance")

        
    def buildProxy(self, url):
        "create AuthProxy objects with our config and the given url"
        url = basicAuthUrl(self.options.zopeusername,
                           self.options.zopepassword,
                           url)
        return CountedProxy.CountedProxy(AuthProxy(url))


    def sendEvent(self, event, **kw):
        'convenience function for pushing events to the Zope server'
        ev = event.copy()
        ev.update(COMMON_EVENT_INFO)
        ev.update(kw)
        #self.log.debug(ev)
        self.zem.callRemote('sendEvent', ev).addErrback(self.log.error)


    def maybeQuit(self):
        "Stop if all performance has been fetched, and we aren't cycling"
        if self.status.finished() and CountedProxy.allFinished():
            if not self.options.daemon and not self.options.cycle:
                reactor.stop()


    def setUnresponsiveDevices(self, deviceList):
        "remember all the unresponsive devices"
        self.log.debug('Unresponsive devices: %r' % deviceList)
        self.unresponsiveDevices = Set(firsts(deviceList))
        

    def cycle(self, seconds, callable):
        "callLater if we should be cycling"
        if self.options.debug:
            seconds /= 60
        reactor.callLater(seconds, callable)


    def startUpdateConfig(self):
        'Periodically ask the Zope server for basic configuration data.'
        lst = []
        deferred = self.model.callRemote('getDevices')
        deferred.addCallbacks(self.updateDeviceList, self.log.debug)
        lst.append(deferred)

        deferred = self.model.callRemote('getDefaultRRDCreateCommand')
        deferred.addCallbacks(self.setRRDCreateCommand, self.log.debug)
        lst.append(deferred)

        deferred = self.model.callRemote('propertyItems')
        deferred.addCallbacks(self.monitorConfigDefaults, self.log.error)
        lst.append(deferred)

        proxy = self.buildProxy(self.options.zem)
        deferred = proxy.callRemote('getDevicePingIssues')
        deferred.addCallbacks(self.setUnresponsiveDevices, self.log.error)
        lst.append(deferred)

        if not self.configLoaded.called:
            defer.DeferredList(lst).chainDeferred(self.configLoaded)

        self.cycle(self.configCycleInterval * 60, self.startUpdateConfig)


    def monitorConfigDefaults(self, items):
        'Unpack config defaults for this monitor'
        table = dict(items)
        for name in ('configCycleInterval', 'snmpCycleInterval'):
            if table.has_key(name):
                value = table[name]
                if getattr(self, name) != value:
                    self.log.debug('Updated %s config to %s' % (name, value))
                setattr(self, name, value)


    def updateDeviceList(self, deviceList):
        'Update the config for devices devices'
        if self.options.device:
            self.log.debug('Gathering performance data for %s ' %
                           self.options.device)
            deviceList = [n for n in deviceList if n[0] == self.options.device]
        self.log.debug('Configured %d devices' % len(deviceList))

        if not deviceList: self.log.warn("no devices found")

        for snmpTargets in deviceList:
            self.updateDeviceConfig(snmpTargets)
            
        # stop collecting those no longer in the list
        deviceNames = Set(firsts(deviceList))
        doomed = Set(self.proxies.keys()) - deviceNames
        for name in doomed:
            self.log.debug('removing device %s' % name)
            del self.proxies[name]
            # we could delete the RRD files, too


    def setRRDCreateCommand(self, command):
        self.defaultRRDCreateCommand = command

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
                           allowCache=False)
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
        (deviceName, snmpStatus, hostPort, snmpConfig, oidData) = snmpTargets
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


    def readDevices(self, unused=None):
        'Periodically fetch the performance values from all known devices'
        self.cycle(self.snmpCycleInterval, self.readDevices)
        
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
        self.sendEvent(self.heartbeat, timeout=self.snmpCycleInterval * 3)
        self.maybeQuit()

    def startReadDevice(self, deviceName):
        '''Initiate a request (or several) to read the performance data
        from a device'''
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        lst = []
        # ensure that the request will fit in a packet
        n = MAX_OIDS_PER_REQUEST
        if proxy.singleOidMode:
            n = 1
        for part in chunk(proxy.oidMap.keys(), n):
            lst.append(proxy.get(part, proxy.timeout, proxy.tries))
        d = defer.DeferredList(lst, consumeErrors=True)
        d.addCallback(self.storeValues, deviceName)
        return d

    def storeValues(self, updates, deviceName):
        'decode responses from devices and store the elements in RRD files'

        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        
        singleOidMode = False
        oids = []
        for success, update in updates:
            if success:
                # failure to report is probably a bad OID
                if not update and not proxy.singleOidMode:
                    singleOidMode = True
                for oid, value in update.items():
                    oids.append(oid)
                    # performance monitoring should always get something back
                    if value == '':
                        self.log.warn('Suspect oid %s is bad' % oid)
                        del proxy.oidMap[oid]
                    else:
                        self.storeRRD(deviceName, oid, value)
        if proxy.singleOidMode:
            # remove any oids that didn't report
            for doomed in Set(proxy.oidMap.keys()) - Set(oids):
                self.log.warn('Suspect oid %s on %s is bad', doomed, deviceName)
                del proxy.oidMap[doomed]
        proxy.singleOidMode = singleOidMode
        if proxy.singleOidMode:
            # fetch this device again, ASAP
            self.status.moreWork(1)
            self.log.warn('Error collecting data on %s, recollecting',
                          deviceName)
            self.startReadDevice(deviceName)
                        
        if self.queryWorkList:
            self.startReadDevice(self.queryWorkList.pop())

        success = reduce(bool.__and__, firsts(updates))
        self.status.record(success)
        proxy.snmpStatus.updateStatus(deviceName, success, self.sendEvent)

    def storeRRD(self, device, oid, value):
        'store a value into an RRD file'
        oidData = self.proxies[device].oidMap[oid]
        
        import rrdtool
        filename = rrdPath(oidData.path)
        if not os.path.exists(filename):
            self.log.debug("create new rrd %s", filename)
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            dataSource = 'DS:%s:%s:%d:0:U' % ('ds0',
                                              oidData.dataStorageType,
                                              3*self.snmpCycleInterval)
            rrdCommand = oidData.rrdCreateCommand
            if not rrdCommand:
                rrdCommand = self.defaultRRDCreateCommand
            if rrdCommand:
                rrdtool.create(filename,
                               "--step",  str(self.snmpCycleInterval),
                               dataSource, *rrdCommand.split())
            else:
                self.log.error('No default RRD create command configured')
                return

        try:
            #self.log.debug("%s %s", filename, value)
            rrdtool.update(filename, 'N:%s' % value)
        except rrdtool.error, err:
            # may get update errors when updating too quickly
            self.log.error('rrd error %s' % err)

        if oidData.dataStorageType == 'COUNTER':
            range, names, values = \
                   rrdtool.fetch(filename, 'AVERAGE',
                                 '-s', 'now-%d' % self.snmpCycleInterval*2,
                                 '-e', 'now')
            value = values[0][0]
        for threshold in oidData.thresholds:
            threshold.check(device, oidData.name, oid, value, self.sendEvent)

    def quit(self, error):
        'stop the reactor if an error occured on the first config load'
        self.log.error(error)
        reactor.stop()

    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZenDaemon.sigTerm(self, signum, frame)
        except SystemExit, ex:
            reactor.stop()

    def main(self):
        "Run forever, fetching and storing"

        self.sendEvent(self.startevt)
        
        zpf.startUpdateConfig()

        reactor.run(installSignalHandlers=False)
        
        self.sendEvent(self.stopevt)


if __name__ == '__main__':
    zpf = zenperfsnmp()
    zpf.main()
