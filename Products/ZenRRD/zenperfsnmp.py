#! /usr/bin/env python 
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

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
import cPickle

from twisted.internet import reactor, defer, error
from twisted.python import failure

import Globals
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.Chain import Chain
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses \
     import Perf_Snmp, Status_Snmp, Status_RRD
from Products.ZenEvents.ZenEventClasses import Critical, Clear

from Products.ZenRRD.RRDUtil import RRDUtil
from SnmpDaemon import SnmpDaemon

from FileCleanup import FileCleanup

# PerformanceConfig import needed to get pb to work
from Products.ZenHub.services.PerformanceConfig import PerformanceConfig
unused(PerformanceConfig)

MAX_OIDS_PER_REQUEST = 40
MAX_SNMP_REQUESTS = 20
DEVICE_LOAD_CHUNK_SIZE = 2

def makeDirs(dir):
    if not os.path.exists(dir):
        os.makedirs(dir, 0750)

def read(fname):
    if os.path.exists(fname):
        fp = file(fname, 'rb')
        try:
            return fp.read()
        finally:
            fp.close()
    return ''

def write(fname, data):
    makeDirs(os.path.dirname(fname))
    fp = open(fname, 'wb')
    try:
        fp.write(data)
    finally:
        fp.close()

def unlink(fname):
    if os.path.exists(fname):
        os.unlink(fname)

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

def checkException(alog, function, *args, **kw):
    try:
        return function(*args, **kw)
    except Exception, ex:
        alog.exception(ex)
        raise ex

from twisted.spread import pb
class SnmpConfig(pb.Copyable, pb.RemoteCopy):
    "A class to transfer the SNMP collection data to zenperfsnmp"

    lastChangeTime = 0.
    device = ''
    connInfo = None
    thresholds = []
    oids = []

pb.setUnjellyableForClass(SnmpConfig, SnmpConfig)

        
class Status:
    'keep track of the status of many parallel requests'
    _success = _fail = 0
    _startTime = _stopTime = 0.0
    _deferred = None

    def __init__(self):
        self._allDevices = Set()
        self._reported = Set()
    
    def start(self, devices):
        'start the clock'
        self._allDevices = Set(devices)
        self._reported = Set()
        self._startTime = time.time()
        self._deferred = defer.Deferred()
        self._checkFinished()           # count could be zero
        return self._deferred


    def record(self, name, successOrFailure):
        'Record success or failure'
        if name in self._reported:
            log.error("Device %s is reporting more than once", name)
            return
        self._reported.add(name)
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
        log.info("total=%d good=%d bad=%d time=%f", * self.stats())


    def finished(self):
        'determine if we have finished everything'
        return self.outstanding() <= 0


    def stats(self):
        'provide a summary of the effort'
        age = self._stopTime - self._startTime
        if not self._startTime:
            age = 0.0
        elif not self.finished():
            age = time.time() - self._startTime
        return (len(self._allDevices), self._success, self._fail, age)


    def outstanding(self):
        'return the number of unfinished operations'
        return len(self.outstandingNames())

    def outstandingNames(self):
        'return the number of unfinished operations'
        return self._allDevices - self._reported


class SnmpStatus:
    "track and report SNMP status failures"

    snmpStatusEvent = {'eventClass': Status_Snmp,
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
                    severity=Event.Error)
            log.warn(summary)
            self.count += 1


class OidData:
    def update(self, name, path, dataStorageType, rrdCreateCommand, minmax):
        self.name = name
        self.path = path
        self.dataStorageType = dataStorageType
        self.rrdCreateCommand = rrdCreateCommand
        self.minmax = minmax


class zenperfsnmp(SnmpDaemon):
    "Periodically query all devices for SNMP values to archive in RRD files"
    
    # these names need to match the property values in StatusMonitorConf
    maxRrdFileAge = 30 * (24*60*60)     # seconds
    perfsnmpConfigInterval = 20*60
    perfsnmpCycleInterval = 5*60
    properties = SnmpDaemon.properties + ('perfsnmpCycleInterval',)
    initialServices = SnmpDaemon.initialServices + ['SnmpPerfConfig']

    def __init__(self):
        SnmpDaemon.__init__(self, 'zenperfsnmp')
        self.status = None
        self.proxies = {}
        self.queryWorkList = Set()
        self.unresponsiveDevices = Set()
        self.snmpOidsRequested = 0
        perfRoot = performancePath('')
        makeDirs(perfRoot)
        self.loadConfigs()
        self.oldFiles = Set()
        # report on files older than a day
        self.oldCheck = FileCleanup(perfRoot, '.*\\.rrd$',
                                    24 * 60 * 60,
                                    frequency=60)
        self.oldCheck.process = self.reportOldFile
        self.oldCheck.start()
        # remove files older than maxRrdFileAge
        self.fileCleanup = FileCleanup(perfRoot, '.*\\.rrd$',
                                       self.maxRrdFileAge,
                                       frequency=90*60)
        self.fileCleanup.process = self.cleanup
        self.fileCleanup.start()

    def pickleName(self, id):
        return performancePath('Devices/%s/%s-config.pickle' % (id, self.options.monitor))

    def loadConfigs(self):
        "Read local configuration values at startup"
        base = performancePath('Devices')
        makeDirs(base)
        root, ds, fs = os.walk(base).next()
        for d in ds:
            config = read(self.pickleName(d))
            if config:
                try:
                    self.updateDeviceConfig(cPickle.loads(config))
                except Exception, ex:
                    self.log.debug("Ignoring updateDeviceConfigFailure: %s", ex)
                    try:
                        os.unlink(self.pickleName(d))
                    except:
                        pass

    def cleanup(self, fullPath):
        self.log.warning("Deleting old RRD file: %s", fullPath)
        os.unlink(fullPath)
        self.oldFiles.discard(fullPath)

    def reportOldFile(self, fullPath):
        self.oldFiles.add(fullPath)

    def maybeQuit(self):
        "Stop if all performance has been fetched, and we aren't cycling"
        if not self.options.daemon and \
           not self.options.cycle:
            reactor.callLater(0, reactor.stop)

    def remote_updateDeviceList(self, devices):
        SnmpDaemon.remote_updateDeviceList(self, devices)
        updated = []
        doomed = Set(self.proxies.keys())
        for device, lastChange in devices:
            doomed.discard(device)
            proxy = self.proxies.get(device)
            if not proxy or proxy.lastChange < lastChange:
                updated.append(device)
        log.info("Deleting %s", doomed)
        for d in doomed:
            del self.proxies[d]
        if updated:
            log.info("Fetching configs: %s", updated)
            d = self.model().callRemote('getDevices', updated)
            d.addCallback(self.updateDeviceList, updated)
            d.addErrback(self.error)

    def startUpdateConfig(self, driver):
        'Periodically ask the Zope server for basic configuration data.'

        now = time.time()
        
        log.info("fetching property items")
        yield self.model().callRemote('propertyItems')
        self.setPropertyItems(driver.next())

        driveLater(self.configCycleInterval * 60, self.startUpdateConfig)

        log.info("getting threshold classes")
        yield self.model().callRemote('getThresholdClasses')
        self.remote_updateThresholdClasses(driver.next())
        
        log.info("checking for outdated configs")
        current = [(k, v.lastChange) for k, v in self.proxies.items()]
        yield self.model().callRemote('getDeviceUpdates', current)

        devices = driver.next()
        if self.options.device:
            devices = [self.options.device]

        log.info("fetching configs for %s", repr(devices)[0:800]+'...')
        yield self.model().callRemote('getDevices', devices)
        updatedDevices = driver.next()

        log.info("fetching default RRDCreateCommand")
        yield self.model().callRemote('getDefaultRRDCreateCommand')
        createCommand = driver.next()

        self.rrd = RRDUtil(createCommand, self.perfsnmpCycleInterval)

        log.info("getting collector thresholds")
        yield self.model().callRemote('getCollectorThresholds')
        self.rrdStats.config(self.options.monitor, self.name, driver.next(),
                             createCommand)
                
        log.info("fetching snmp status")
        yield self.model().callRemote('getSnmpStatus', self.options.device)
        self.updateSnmpStatus(driver.next())

        # Kick off the device load
        log.info("Initiating incremental device load")
        d = self.updateDeviceList(updatedDevices, devices)
        def report(result):
            if result:
                log.error("Error loading devices: %s", result)
        d.addBoth(report)
        self.sendEvents(self.rrdStats.gauge('configTime',
                                            self.configCycleInterval * 60,
                                            time.time() - now))


    def updateDeviceList(self, responses, requested):
        'Update the config for devices devices'
        def fetchDevices(driver):
            deviceNames = Set()
            length = len(responses)
            log.debug("Fetching configs for %d devices", length)
            for devices in chunk(responses, DEVICE_LOAD_CHUNK_SIZE):
                log.debug("Fetching config for %s", devices)
                yield self.model().callRemote('getDeviceConfigs', devices)
                try:
                    for response in driver.next():
                       self.updateDeviceConfig(response)
                except Exception, ex:
                    log.warning("Error loading config for devices %s" % devices)
                for d in devices:
                    deviceNames.add(d)
            log.debug("Finished fetching configs for %d devices", length)

            # stop collecting those no longer in the list
            doomed = Set(requested) - deviceNames
            if self.options.device:
                self.log.debug('Gathering performance data for %s ' %
                               self.options.device)
                doomed = Set(self.proxies.keys())
                doomed.discard(self.options.device)
            for name in doomed:
                self.log.info('removing device %s' % name)
                if name in self.proxies:
                    del self.proxies[name]
                config = self.pickleName(name)
                unlink(config)
                # we could delete the RRD files, too

            ips = Set()
            for name, proxy in self.proxies.items():
                if proxy.snmpConnInfo.manageIp in ips:
                    log.warning("Warning: device %s has a duplicate address %s",
                                name, proxy.snmpConnInfo.manageIp)
                ips.add(proxy.snmpConnInfo.manageIp)
            self.log.info('Configured %d of %d devices',
                          len(deviceNames), len(self.proxies))
            yield defer.succeed(None)
        return drive(fetchDevices)


    def updateAgentProxy(self, deviceName, snmpConnInfo):
        "create or update proxy"
        p = self.proxies.get(deviceName, None)
        if not p:
            p = snmpConnInfo.createSession(protocol=self.snmpPort.protocol,
                                           allowCache=True)
            p.oidMap = {}
            p.snmpStatus = SnmpStatus(0)
            p.singleOidMode = False
            p.lastChange = 0
        if p.snmpConnInfo != snmpConnInfo:
            t = snmpConnInfo.createSession(protocol=self.snmpPort.protocol,
                                           allowCache=True)
            t.oidMap = p.oidMap
            t.snmpStatus = p.snmpStatus
            t.singleOidMode = p.singleOidMode
            t.lastChange = p.lastChange
            p = t
        return p

    def updateSnmpStatus(self, status):
        "Update the Snmp failure counts from Status database"
        countMap = dict(status)
        for name, proxy in self.proxies.items():
            proxy.snmpStatus.count = countMap.get(name, 0)


    def remote_deleteDevice(self, doomed):
        self.log.debug("Async delete device %s" % doomed)
        if doomed in self.proxies:
             del self.proxies[doomed]


    def remote_updateDeviceConfig(self, snmpTargets):
        self.log.debug("Async device update")
        self.updateDeviceConfig(snmpTargets)


    def updateDeviceConfig(self, snmpTargets):
        'Save the device configuration and create an SNMP proxy to talk to it'
        cfg = snmpTargets

        self.log.debug("received config for %s", cfg.device)
        p = self.updateAgentProxy(cfg.device, cfg.connInfo)
        if p.lastChange < cfg.lastChangeTime:
            p.lastChange = cfg.lastChangeTime
            write(self.pickleName(cfg.device), cPickle.dumps(snmpTargets))

        oidMap, p.oidMap = p.oidMap, {}
        for name, oid, path, dsType, createCmd, minmax in cfg.oids:
            createCmd = createCmd.strip()
            oid = str(oid).strip('.')
            # beware empty oids
            if oid:
                oid = '.' + oid
                p.oidMap[oid] = d = oidMap.setdefault(oid, OidData())
                d.update(name, path, dsType, createCmd, minmax)
        self.proxies[cfg.device] = p
        self.thresholds.updateForDevice(cfg.device, cfg.thresholds)


    def scanCycle(self, *unused):
        reactor.callLater(self.perfsnmpCycleInterval, self.scanCycle)
        self.log.debug("getting device ping issues")
        evtSvc = self.services.get('EventService', None)
        if evtSvc:
            d = evtSvc.callRemote('getDevicePingIssues')
            d.addBoth(self.setUnresponsiveDevices)


    def setUnresponsiveDevices(self, arg):
        "remember all the unresponsive devices"
        if isinstance(arg, list):
            deviceList = arg
            self.log.debug('unresponsive devices: %r' % deviceList)
            self.unresponsiveDevices = Set(firsts(deviceList))
        else:
            self.log.error('Could not get unresponsive devices: %s', arg)
        self.readDevices()

        
    def readDevices(self, unused=None):
        'Periodically fetch the performance values from all known devices'
        
        if self.status and not self.status.finished():
            _, _, _, age = self.status.stats()
            self.log.warning("There are still %d devices to query",
                             self.status.outstanding())
            self.log.warning("Problem devices: %r",
                             list(self.status.outstandingNames()))
            if age < self.perfsnmpCycleInterval * 2:
                self.log.warning("Waiting one more cycle period")
                return
            self.log.warning("Devices status is not clearing.  Restarting.")

        self.queryWorkList =  Set(self.proxies.keys())
        self.queryWorkList -= self.unresponsiveDevices
        self.status = Status()
        d = self.status.start(self.queryWorkList)
        d.addCallback(self.reportRate)
        for unused in range(MAX_SNMP_REQUESTS):
            if not self.queryWorkList: break
            d = self.startReadDevice(self.queryWorkList.pop())
            def printError(reason):
                from StringIO import StringIO
                out = StringIO()
                reason.printTraceback(out)
                self.log.error(reason)
            d.addErrback(printError)


    def reportRate(self, *unused):
        'Finished reading all the devices, report stats and maybe stop'
        total, success, failed, runtime = self.status.stats()
        oidsRequested, self.snmpOidsRequested = self.snmpOidsRequested, 0
        self.log.info("sent %d OID requests", oidsRequested)
        self.log.info("collected %d of %d devices in %.2f" %
                      (success, total, runtime))
        self.heartbeat()
        
        cycle = self.perfsnmpCycleInterval
        self.sendEvents(
            self.rrdStats.gauge('success', cycle, success) + 
            self.rrdStats.gauge('failed', cycle, failed) +
            self.rrdStats.gauge('cycleTime', cycle, runtime) +
            self.rrdStats.counter('dataPoints', cycle, self.rrd.dataPoints) +
            self.rrdStats.gauge('cyclePoints', cycle, self.rrd.endCycle())
            )
        # complain about RRD files that have not been updated
        self.checkOldFiles()

    def checkOldFiles(self):
        self.oldFiles = Set(
            [f for f in self.oldFiles
             if os.path.exists(f) and self.oldCheck.test(f)]
            )
        if self.oldFiles:
            root = performancePath('')
            filenames = [f.lstrip(root) for f in self.oldFiles]
            message = 'RRD files not updated: ' + ' '.join(filenames)
            self.sendEvent(dict(
                severity=Critical,
                device=self.options.monitor,
                eventClass=Status_RRD,
                summary=message))
        else:
            self.sendEvent(dict(
                severity=Clear, 
                device=self.options.monitor,
                eventClass=Status_RRD,
                summary='All RRD files have been recently update'))


    def startReadDevice(self, deviceName):
        '''Initiate a request (or several) to read the performance data
        from a device'''
        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            return
        # ensure that the request will fit in a packet
        n = int(proxy.snmpConnInfo.zMaxOIDPerRequest)
        if proxy.singleOidMode:
            n = 1
        def getLater(oids):
            return checkException(self.log,
                                  proxy.get,
                                  oids,
                                  proxy.snmpConnInfo.zSnmpTimeout,
                                  proxy.snmpConnInfo.zSnmpTries)
        proxy.open()
        chain = Chain(getLater, iter(chunk(sorted(proxy.oidMap.keys()), n)))
        d = chain.run()
        def closer(arg, proxy):
            checkException(self.log, proxy.close)
            return arg
        d.addCallback(closer, proxy)
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
                       eventClass=Perf_Snmp,
                       device=deviceName,
                       summary=summary,
                       component=name,
                       severity=Event.Info)
        self.log.warn(summary)
        del proxy.oidMap[oid]
        

    def storeValues(self, updates, deviceName):
        'decode responses from devices and store the elements in RRD files'

        proxy = self.proxies.get(deviceName, None)
        if proxy is None:
            self.status.record(deviceName, True)
            return

        # Look for problems
        for success, update in updates:
            # empty update is probably a bad OID in the request somewhere
            if success and not update and not proxy.singleOidMode:
                proxy.singleOidMode = True
                self.log.warn('Error collecting data on %s, recollecting',
                              deviceName)
                self.startReadDevice(deviceName)
                return
            if not success:
                if isinstance(update, failure.Failure) and \
                    isinstance(update.value, error.TimeoutError):
                    self.log.debug("Device %s timed out" % deviceName)
                else:
                    self.log.error('Failed to collect on %s (%s: %s)',
                                   deviceName,
                                   update.__class__,
                                   update)
                
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
        self.status.record(deviceName, success)
        proxy.snmpStatus.updateStatus(deviceName, success, self.sendEvent)


    def storeRRD(self, device, oid, value):
        'store a value into an RRD file'
        oidData = self.proxies[device].oidMap.get(oid, None)
        if not oidData: return

        min, max = oidData.minmax
        value = self.rrd.save(oidData.path,
                              value,
                              oidData.dataStorageType,
                              oidData.rrdCreateCommand,
                              min=min, max=max)

        for ev in self.thresholds.check(oidData.path, time.time(), value):
            ev['eventKey'] = oid
            self.sendThresholdEvent(**ev)

    def connected(self):
        "Run forever, fetching and storing"
        d = drive(self.startUpdateConfig)
        d.addCallbacks(self.scanCycle, self.errorStop)


if __name__ == '__main__':
    from Products.ZenRRD.zenperfsnmp import zenperfsnmp
    zpf = zenperfsnmp()
    zpf.run()
