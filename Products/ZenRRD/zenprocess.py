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

__doc__= """zenprocess

Gets SNMP process performance data and stores it in RRD files.
"""

import logging
import time
from sets import Set

log = logging.getLogger("zen.zenprocess")

from twisted.internet import reactor, defer, error

import Globals
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.NJobs import NJobs
from Products.ZenUtils.Chain import Chain
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_Snmp, \
      Status_OSProcess, Critical, Status_Perf

from Products.ZenRRD.RRDUtil import RRDUtil
from SnmpDaemon import SnmpDaemon

from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
# needed for pb comms
SnmpConnInfo = SnmpConnInfo

HOSTROOT  ='.1.3.6.1.2.1.25'
RUNROOT   = HOSTROOT + '.4'
NAMETABLE = RUNROOT + '.2.1.2'
PATHTABLE = RUNROOT + '.2.1.4'
ARGSTABLE = RUNROOT + '.2.1.5'
PERFROOT  = HOSTROOT + '.5'
CPU       = PERFROOT + '.1.1.1.'        # note trailing dot
MEM       = PERFROOT + '.1.1.2.'        # note trailing dot

DEFAULT_PARALLEL_JOBS = 10

WRAP=0xffffffffL

try:
    sorted = sorted                     # added in python 2.4
except NameError:
    def sorted(x, *args, **kw):
        x.sort(*args, **kw)
        return x

def reverseDict(d):
    """return a dictionary with keys and values swapped:
    all values are lists to handle the different keys mapping to the same value
    """
    result = {}
    for a, v in d.items():
        result.setdefault(v, []).append(a)
    return result

def chunk(lst, n):
    'break lst into n-sized chunks'
    return [lst[i:i+n] for i in range(0, len(lst), n)]

class ScanFailure(Exception): pass

class Pid:
    cpu = None
    memory = None

    def updateCpu(self, n):
        if n is not None:
            try:
                n = int(n)
            except ValueError, er:
                log.warning("Bad value for CPU: '%s'", n)

        if self.cpu is None or n is None:
            self.cpu = n
            return None
        diff = n - self.cpu
        if diff < 0:
            # don't provide a value when the counter falls backwards
            n = None
            diff = None
        self.cpu = n
        return diff

    def updateMemory(self, n):
        self.memory = n

    def __str__(self):
        return '<Pid> memory: %s cpu: %s' % (self.memory, self.cpu)
    __repr__ = __str__


from twisted.spread import pb
class Process(pb.Copyable, pb.RemoteCopy):
    'track process-specific configuration data'
    name = None
    originalName = None
    ignoreParameters = False
    restart = None
    severity = Event.Warning
    status = 0
    cpu = 0
    cycleTime = None

    def __init__(self):
        self.pids = {}

    def match(self, name, args):
        if self.name is None:
            return False
        if self.ignoreParameters or not args:
            return self.originalName == name
        return self.originalName == '%s %s' % (name, args)

    def __str__(self):
        return str(self.name)
    __repr__ = __str__

    def updateCpu(self, pid, value):
        p = self.pids.setdefault(pid, Pid())
        cpu = p.updateCpu(value)
        if cpu is not None:
            self.cpu += cpu
            self.cpu %= WRAP

    def getCpu(self):
        return self.cpu

    def updateMemory(self, pid, value):
        self.pids.setdefault(pid, Pid()).memory = value

    def getMemory(self):
        return sum([x.memory for x in self.pids.values()
                    if x.memory is not None])

    def discardPid(self, pid):
        if self.pids.has_key(pid):
            del self.pids[pid]

    def updateConfig(self, update):
        if self is update:
            return
        self.name = update.name
        self.originalName = update.originalName
        self.ignoreParameters = update.ignoreParameters
        self.restart = update.restart
        self.severity = update.severity

pb.setUnjellyableForClass(Process, Process)

class Device(pb.Copyable, pb.RemoteCopy):
    'track device data'
    name = ''
    snmpConnInfo = None
    proxy = None
    lastScan = 0.
    snmpStatus = 0
    lastChange = 0
    maxOidsPerRequest = 40

    def __init__(self):
        # map process name to Process object above
        self.processes = {}
        # map pid number to Process object
        self.pids = {}

    def open(self):
        self._makeProxy()

    def close(self, unused=None):
        if self.proxy:
            self.proxy.close()
        self.proxy = None
        return unused

    def _makeProxy(self):
        p = self.proxy
        c = self.snmpConnInfo
        if (p is None or p.snmpConnInfo != c):
            self.proxy = self.snmpConnInfo.createSession()
            self.proxy.open()
    
    def updateConfig(self, cfg):
        if self is cfg:
            return
        self.snmpConnInfo = cfg.snmpConnInfo
        unused = Set(self.processes.keys())
        for update in cfg.processes.values():
            unused.discard(update.name)
            p = self.processes.setdefault(update.name, Process())
            p.updateConfig(update)
        for name in unused:
            del self.processes[name]


    def get(self, oids):
        return self.proxy.get(oids,
                              self.snmpConnInfo.zSnmpTimeout,
                              self.snmpConnInfo.zSnmpTries)


    def getTables(self, oids):
        repetitions = self.maxOidsPerRequest / len(oids)
        t = self.proxy.getTable(oids,
                                timeout=self.snmpConnInfo.zSnmpTimeout,
                                retryCount=self.snmpConnInfo.zSnmpTries,
                                maxRepetitions=repetitions)
        return t
pb.setUnjellyableForClass(Device, Device)


class zenprocess(SnmpDaemon):
    statusEvent = { 'eventClass' : Status_OSProcess,
                    'eventGroup' : 'Process' }
    initialServices = SnmpDaemon.initialServices + ['ProcessConfig']
    processConfigInterval = 20*60
    processCycleInterval = 5*60
    properties = SnmpDaemon.properties + ('processCycleInterval',)
    missing = 0
    restarted = 0
    parallelJobs = DEFAULT_PARALLEL_JOBS

    def __init__(self, noopts=False):
        SnmpDaemon.__init__(self, 'zenprocess', noopts)
        self._devices = {}
        self.scanning = None
        self.downDevices = Set()

    def devices(self):
        "Return a filtered list of devices"
        return dict([(k, v) for k, v in self._devices.items()
                     if k not in self.downDevices])

    def fetchConfig(self):
        'Get configuration values from the Zope server'
        def doFetchConfig(driver):
            now = time.time()
            
            yield self.model().callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()

            yield self.model().callRemote('getZenProcessParallelJobs')
            self.parallelJobs = int(driver.next())

            yield self.model().callRemote('propertyItems')
            self.setPropertyItems(driver.next())

            self.rrd = RRDUtil(createCommand, self.processCycleInterval)

            yield self.model().callRemote('getThresholdClasses')
            self.remote_updateThresholdClasses(driver.next())

            yield self.model().callRemote('getCollectorThresholds')
            self.rrdStats.config(self.options.monitor,
                                 self.name,
                                 driver.next(),
                                 createCommand)

            devices = []
            if self.options.device:
                devices = [self.options.device]
            yield self.model().callRemote('getOSProcessConf', devices)
            driver.next()
            self.sendEvents(
                self.rrdStats.gauge('configTime',
                                    self.processConfigInterval,
                                    time.time() - now)
                )

        return drive(doFetchConfig)

    def remote_deleteDevice(self, doomed):
        self.log.debug("Async delete device %s" % doomed)
        if doomed in self._devices:
             del self._devices[doomed]
        self.clearSnmpError(doomed, "Device %s removed from SNMP collection")

    def remote_updateDeviceList(self, devices):
        self.log.debug("Async update device list %s" % devices)
        doomed = Set(self._devices.keys())
        updated = []
        for device, lastChange in devices:
            cfg = self._devices.get(device, None)
            if not cfg or self._devices[device].lastChange < lastChange:
                updated.append(device)
            doomed.discard(device)
        if updated:
            log.info("Fetching the config for %s", updated)
            d = self.model().callRemote('getOSProcessConf', devices)
            d.addCallback(self.updateDevices, updated)
            d.addErrback(self.error)
        if doomed:
            log.info("Removing %s", doomed)
            for device in doomed:
                del self._devices[device]
                self.clearSnmpError(device, "device %s removed" % device)


    def clearSnmpError(self, name, message):
        if name in self._devices:
            if self._devices[name].snmpStatus > 0:
                self._devices[name].snmpStatus = 0
                self.sendEvent(self.statusEvent,
                               eventClass=Status_Snmp,
                               component="process",
                               device=name,
                               summary=message,
                               severity=Event.Clear)
            

    def remote_updateDevice(self, cfg):
        self.log.debug("Async config update for %s", cfg.name)
        self.updateDevices([cfg],[])

    
    def updateDevices(self, cfgs, fetched):
        received = Set()
        for cfg in cfgs:
            received.add(cfg.name)
            d = self._devices.setdefault(cfg.name, cfg)
            d.updateConfig(cfg)
            self.thresholds.updateForDevice(cfg.name, cfg.thresholds)
        for doomed in Set(fetched) - received:
            if doomed in self._devices:
                del self._devices[doomed]

    def start(self, driver):
        'Read the basic config needed to do anything'
        log.debug("fetching config")
        devices = self._devices.keys()
        yield self.fetchConfig()
        self.updateDevices(driver.next(), devices)

        yield self.model().callRemote('getSnmpStatus', self.options.device)
        self.updateSnmpStatus(driver.next())

        yield self.model().callRemote('getProcessStatus', self.options.device)
        self.updateProcessStatus(driver.next())

        driveLater(self.configCycleInterval * 60, self.start)


    def updateSnmpStatus(self, updates):
        for name, count in updates:
            d = self._devices.get(name)
            if d:
                d.snmpStatus = count


    def updateProcessStatus(self, status):
        down = {}
        for device, component, count in status:
            down[ (device, component) ] = count
        for name, device in self._devices.items():
            for p in device.processes.values():
                p.status = down.get( (name, p.originalName), 0)


    def oneDevice(self, device):
        device.open()
        def go(driver):
            yield self.scanDevice(device)
            driver.next()
            yield self.fetchPerf(device)
            driver.next()
        d = drive(go)
        d.addBoth(device.close)
        return d
        

    def scanDevice(self, device):
        "Fetch all the process info"
        device.lastScan = time.time()
        tables = [NAMETABLE, PATHTABLE, ARGSTABLE]
        d = device.getTables(tables)
        d.addCallback(self.storeProcessNames, device)
        d.addErrback(self.deviceFailure, device)
        return d


    def deviceFailure(self, reason, device):
        "Log exception for a single device"
        self.sendEvent(self.statusEvent,
                       eventClass=Status_Snmp,
                       component="process",
                       device=device.name,
                       summary='Unable to read processes on device %s' % device.name,
                       severity=Event.Error)
        device.snmpStatus += 1
        if isinstance(reason.value, error.TimeoutError):
            self.log.debug('Timeout on device %s' % device.name)
        else:
            self.logError('Error on device %s' % device.name, reason.value)


    def storeProcessNames(self, results, device):
        "Parse the process tables and figure what pids are on the device"
        if not results:
            summary = 'Device %s does not publish HOST-RESOURCES-MIB' % device.name
            self.sendEvent(self.statusEvent,
                           device=device.name,
                           summary=summary,
                           severity=Event.Error)
            log.info(summary)
            return
        if device.snmpStatus > 0:
            summary = 'Process table up for device %s' % device.name
            self.clearSnmpError(device.name, summary)
            
        procs = []
        names, paths, args = {}, {}, {}
        def extract(dictionary, oid, value):
            pid = int(oid.split('.')[-1])
            dictionary[pid] = value
        for row in results[NAMETABLE].items():
            extract(names, *row)
        for row in results[PATHTABLE].items():
            extract(paths, *row)
        for row in results[ARGSTABLE].items():
            extract(args,  *row)
        for i, path in paths.items():
            if i not in names: continue
            name = names[i]
            if path and path.find('\\') == -1:
                name = path
            arg = ''
            if i in args: arg = args[i]
            procs.append( (i, (name, arg) ) )
        # look for changes in pids
        before = Set(device.pids.keys())
        after = {}
        for p in device.processes.values():
            for pid, (name, args) in procs:
                if p.match(name, args):
                    log.debug("Found process %d on %s" % (pid, p.name))
                    after[pid] = p
        afterSet = Set(after.keys())
        afterByConfig = reverseDict(after)
        new =  afterSet - before
        dead = before - afterSet

        # report pid restarts
        for p in dead:
            config = device.pids[p]
            config.discardPid(p)
            if afterByConfig.has_key(config):
                self.restarted += 1
                if config.restart:
                    summary = 'Process restarted: %s' % config.originalName
                    self.sendEvent(self.statusEvent,
                                   device=device.name,
                                   summary=summary,
                                   component=config.originalName,
                                   severity=config.severity)
                    log.info(summary)
            
        # report alive processes
        for config, pids in afterByConfig.items():
            summary = "Process up: %s" % config.originalName
            self.sendEvent(self.statusEvent,
                           device=device.name,
                           summary=summary,
                           component=config.originalName,
                           severity=Event.Clear)
            config.status = 0
            log.debug(summary)

        for p in new:
            log.debug("Found new %s pid %d on %s" % (
                after[p].originalName, p, device.name))
        device.pids = after

        # no pids for a config
        for config in device.processes.values():
            if not afterByConfig.has_key(config):
                self.missing += 1
                config.status += 1
                summary = 'Process not running: %s' % config.originalName
                self.sendEvent(self.statusEvent,
                               device=device.name,
                               summary=summary,
                               component=config.originalName,
                               severity=config.severity)
                log.warning(summary)
        
        # store counts
        pidCounts = dict([(p, 0) for p in device.processes])
        for pids, pidConfig in device.pids.items():
            pidCounts[pidConfig.name] += 1
        for name, count in pidCounts.items():
            self.save(device.name, name, 'count_count', count, 'GAUGE')


    def periodic(self, unused=None):
        "Basic SNMP scan loop"
        reactor.callLater(self.processCycleInterval, self.periodic)

        if self.scanning:
            running, unstarted, finished = self.scanning.status()
            msg = "performance scan job not finishing: " \
                  "%d jobs running %d jobs waiting %d jobs finished" % \
                  (running, unstarted, finished)
            log.error(msg)
            return

        start = time.time()

        def doPeriodic(driver):

            yield self.getDevicePingIssues()
            self.downDevices = Set([d[0] for d in driver.next()])

            self.scanning = NJobs(self.parallelJobs,
                                  self.oneDevice,
                                  self.devices().values())
            yield self.scanning.start()
            driver.next()

        def checkResults(results):
            for result in results:
                if isinstance(result , Exception):
                    log.error("Error scanning device: %s", result)
                    break
            else:
                self.cycleTime = time.time() - start
                self.heartbeat()

        drive(doPeriodic).addCallback(checkResults)


    def fetchPerf(self, device):
        "Get performance data for all the monitored Processes on a device"
        oids = []
        for pid, pidConf in device.pids.items():
            oids.extend([CPU + str(pid), MEM + str(pid)])
        if not oids:
            return defer.succeed(([], device))
        
        d = Chain(device.get, iter(chunk(oids, device.maxOidsPerRequest))).run()
        d.addBoth(self.storePerfStats, device)
        return d


    def storePerfStats(self, results, device):
        "Save the performance data in RRD files"
        for success, result in results:
            if not success:
                self.error(result)
                return results
        self.clearSnmpError(device.name,
                            'Process table up for device %s' % device.name)
        parts = {}
        for success, values in results:
            if success:
                parts.update(values)
        results = parts
        byConf = reverseDict(device.pids)
        for pidConf, pids in byConf.items():
            if len(pids) != 1:
                log.info("There are %d pids by the name %s",
                         len(pids), pidConf.name)
            pidName = pidConf.name
            for pid in pids:
                cpu = results.get(CPU + str(pid), None)
                mem = results.get(MEM + str(pid), None)
                pidConf.updateCpu(pid, cpu)
                pidConf.updateMemory(pid, mem)
            self.save(device.name, pidName, 'cpu_cpu', pidConf.getCpu(),
                      'DERIVE', min=0)
            self.save(device.name, pidName, 'mem_mem', pidConf.getMemory() * 1024,
                      'GAUGE')


    def save(self, deviceName, pidName, statName, value, rrdType,
             min='U', max='U'):
        """
        Save a value into an RRD file

        @param deviceName: name of the remote device (ie a hostname)
        @type deviceName: string
        @param pidName: process id of the monitored process
        @type pidName: string
        @param statName: metric name
        @type statName: string
        @param value: data to be stored
        @type value: number
        @param rrdType: RRD data type (eg ABSOLUTE, DERIVE, COUNTER)
        @type rrdType: string
        @param min: minimum value acceptable for this metric
        @type min: number
        @param max: maximum value acceptable for this metric
        @type max: number
        """
        path = 'Devices/%s/os/processes/%s/%s' % (deviceName, pidName, statName)
        try:
            value = self.rrd.save(path, value, rrdType, min=min, max=max)

        except Exception, ex:
            summary= "Unable to save data for process-monitor RRD %s" % \
                              path
            self.log.critical( summary )

            message= "Data was value= %s, type=%s, min=%s, max=%s" % \
                     ( value, rrdType, min, max, )
            self.log.critical( message )
            self.log.exception( ex )

            import traceback
            trace_info= traceback.format_exc()

            evid= self.sendEvent(dict(
                dedupid="%s|%s" % (self.options.monitor, 'RRD write failure'),
                severity=Critical,
                device=self.options.monitor,
                eventClass=Status_Perf,
                component="RRD",
                pidName=pidName,
                statName=statName,
                path=path,
                message=message,
                traceback=trace_info,
                summary=summary))

            # For test harness purposes
            self.last_evid= evid

            # Skip thresholds
            return

        for ev in self.thresholds.check(path, time.time(), value):
            self.sendThresholdEvent(**ev)
            

    def heartbeat(self):
        self.scanning = None
        devices = self.devices()
        pids = sum(map(lambda x: len(x.pids), devices.values()))
        log.info("Pulled process status for %d devices and %d processes",
                 len(devices), pids)
        SnmpDaemon.heartbeat(self)
        cycle = self.processCycleInterval
        self.sendEvents(
            self.rrdStats.counter('dataPoints', cycle, self.rrd.dataPoints) + 
            self.rrdStats.gauge('cyclePoints', cycle, self.rrd.endCycle()) + 
            self.rrdStats.gauge('pids', cycle, pids) +
            self.rrdStats.gauge('devices', cycle, len(devices)) +
            self.rrdStats.gauge('missing', cycle, self.missing) + 
            self.rrdStats.gauge('restarted', cycle, self.restarted) +
            self.rrdStats.gauge('cycleTime', cycle, self.cycleTime)
            )


    def connected(self):
        drive(self.start).addCallbacks(self.periodic, self.errorStop)


if __name__ == '__main__':
    from Products.ZenRRD.zenprocess import zenprocess
    z = zenprocess()
    z.run()
