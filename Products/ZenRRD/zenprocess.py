#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenprocess

Gets snmp process performance data and stores it in RRD files.

$Id$
'''

__version__ = "$Revision$"[11:-2]

import logging
import time
from sets import Set

log = logging.getLogger("zen.zenprocess")

from twisted.internet import reactor, defer

try:
    from pynetsnmp.twistedsnmp import AgentProxy
    from pynetsnmp.tableretriever import TableRetriever
except ImportError:
    import warnings
    warnings.warn("Using python-based snmp enging")
    from twistedsnmp.agentproxy import AgentProxy
    from twistedsnmp.tableretriever import TableRetriever

import Globals
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.NJobs import NJobs
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Status_Snmp, Status_OSProcess

from RRDUtil import RRDUtil
from RRDDaemon import Threshold, ThresholdManager
from SnmpDaemon import SnmpDaemon

HOSTROOT  ='.1.3.6.1.2.1.25'
RUNROOT   = HOSTROOT + '.4'
NAMETABLE = RUNROOT + '.2.1.2'
ARGSTABLE = RUNROOT + '.2.1.5'
PERFROOT  = HOSTROOT + '.5'
CPU       = PERFROOT + '.1.1.1.'        # note trailing dot
MEM       = PERFROOT + '.1.1.2.'        # note trailing dot

PARALLEL_JOBS = 10
MAX_OIDS_PER_REQUEST = 40

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

def closer(value, device):
    device.close()
    return value

class ScanFailure(Exception): pass

class Pid:
    cpu = None
    memory = None

    def updateCpu(self, n):
        if n is not None:
            try:
                n = int(n)
            except ValueError, er:
                log.error("Bad value for CPU: '%s'", n)

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


class Process:
    'track process-specific configuration data'
    name = None
    originalName = None
    ignoreParameters = False
    restart = None
    severity = Event.Warning
    status = 0
    cpu = 0

    def __init__(self):
        self.pids = {}
        self.thresholds = {}

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

class Device:
    'track device data'
    name = ''
    address = ('', 0)
    community = 'public'
    version = '1'
    port = 161
    proxy = None
    timeout = 2.5
    tries = 2
    protocol = None
    lastScan = 0.
    snmpStatus = 0

    def __init__(self):
        # map process name to Process object above
        self.processes = {}
        # map pid number to Process object
        self.pids = {}

    def open(self):
        self._makeProxy()
        if hasattr(self.proxy, 'open'):
            self.proxy.open()

    def close(self):
        if hasattr(self.proxy, 'close'):
            self.proxy.close()

    def _makeProxy(self):
        p = self.proxy
        if (p is None or 
            (p.ip, p.port) != self.address or
            p.snmpVersion != self.version or
            p.port != self.port):
            self.proxy = AgentProxy(ip=self.address[0],
                                    port=self.address[1],
                                    community=self.community,
                                    snmpVersion=self.version,
                                    protocol=self.protocol,
                                    allowCache=True)
            self.proxy.tries = self.tries
            self.proxy.timeout = self.timeout

    
    def updateConfig(self, processes):
        unused = Set(self.processes.keys())
        for name, originalName, ignoreParameters, \
                restart, severity, thresholds \
                in processes:
            unused.discard(name)
            p = self.processes.setdefault(name, Process())
            p.name = name
            p.originalName = originalName
            p.ignoreParameters = ignoreParameters
            p.restart = restart
            p.severity = severity
            p.thresholds, before = {}, p.thresholds
            for name, threshes in thresholds:
                m = before.get(name, ThresholdManager())
                m.update(threshes)
                p.thresholds[name] = m
        for name in unused:
            del self.processes[name]

    def get(self, oids):
        return self.proxy.get(oids, self.timeout, self.tries)


    def getTables(self, oids):
        t = TableRetriever(self.proxy, oids,
                           timeout=self.timeout,
                           retryCount=self.tries,
                           maxRepetitions=MAX_OIDS_PER_REQUEST / len(oids))
        return t()


class zenprocess(SnmpDaemon):
    statusEvent = { 'eventClass' : Status_OSProcess,
                    'eventGroup' : 'Process' }

    def __init__(self):
        SnmpDaemon.__init__(self, 'zenprocess')
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
            yield self.model.callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()

            yield self.model.callRemote('propertyItems')
            self.setPropertyItems(driver.next())

            self.rrd = RRDUtil(createCommand, self.snmpCycleInterval)

            yield self.model.callRemote('getOSProcessConf', self.options.device)
            driver.next()

        return drive(doFetchConfig)


    def start(self, driver):
        'Read the basic config needed to do anything'
        log.debug("fetching config")
        self.syncdb()
        yield self.fetchConfig();
        n = driver.next()
        removed = Set(self._devices.keys())
        for (name, addr, snmpConf), procs in n:
            community, version, timeout, tries = snmpConf
            removed.discard(name)
            d = self._devices.setdefault(name, Device())
            d.name = name
            d.address = addr
            d.community = community
            d.version = version
            d.timeout = timeout
            d.tries = tries
            d.updateConfig(procs)
            d.protocol = self.snmpPort.protocol
        for r in removed:
            del self._devices[r]

        yield self.model.callRemote('getSnmpStatus', self.options.device)
        self.updateSnmpStatus(driver.next())

        yield self.model.callRemote('getProcessStatus', self.options.device)
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
        d.addBoth(closer, device)
        return d
        

    def scanDevice(self, device):
        "Fetch all the process info"
        device.lastScan = time.time()
        tables = [NAMETABLE, ARGSTABLE]
        d = device.getTables(tables)
        d.addCallback(self.storeProcessNames, device)
        d.addErrback(self.deviceFailure, device)
        return d


    def deviceFailure(self, error, device):
        "Log exception for a single device"
        self.sendEvent(self.statusEvent,
                       eventClass=Status_Snmp,
                       component="snmp",
                       device=device.name,
                       summary='Unable to read processes on device %s' % device.name,
                       severity=Event.Error)
        self.logError('Error on device %s' % device.name, error.value)


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
            device.snmpStatus = 0
            summary = 'Good SNMP response from device %s' % device.name
            self.sendEvent(self.statusEvent,
                           eventClass=Status_Snmp,
                           component="snmp",
                           device=device.name,
                           summary=summary,
                           severity=Event.Clear)
        
            
        procs = []
        for namePart, argsPart in zip(sorted(results[NAMETABLE].items()),
                                      sorted(results[ARGSTABLE].items())):
            oid, name = namePart
            namepid = int(oid.split('.')[-1])
            oid, args = argsPart
            argpid = int(oid.split('.')[-1])
            if namepid == argpid:
                procs.append( (namepid, (name, args) ) )
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
            if config.status > 0:
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
                config.status += 1
                summary = 'Process not running: %s' % config.originalName
                self.sendEvent(self.statusEvent,
                               device=device.name,
                               summary=summary,
                               component=config.originalName,
                               severity=config.severity)
                log.error(summary)
        
        # store counts
        pidCounts = dict([(p, 0) for p in device.processes])
        for pids, pidConfig in device.pids.items():
            pidCounts[pidConfig.name] += 1
        for name, count in pidCounts.items():
            self.save(device.name, name, 'count_count', count, 'GAUGE')


    def periodic(self, unused=None):
        "Basic SNMP scan loop"
        reactor.callLater(self.snmpCycleInterval, self.periodic)

        if self.scanning:
            running, unstarted, finished = self.scanning.status()
            msg = "performance scan job not finishing: " \
                  "%d jobs running %d jobs waiting %d jobs finished" % \
                  (running, unstarted, finished)
            log.error(msg)
            return

        def doPeriodic(driver):
            
            yield self.zem.callRemote('getDevicePingIssues')
            self.downDevices = Set([d[0] for d in driver.next()])

            self.scanning = NJobs(PARALLEL_JOBS,
                                  self.oneDevice,
                                  self.devices().values())
            yield self.scanning.start()
            driver.next()

        drive(doPeriodic).addCallback(self.heartbeat)


    def fetchPerf(self, device):
        "Get performance data for all the monitored Processes on a device"
        oids = []
        for pid, pidConf in device.pids.items():
            oids.extend([CPU + str(pid), MEM + str(pid)])
        if not oids:
            return defer.succeed(([], device))
        
        d = device.get(oids)
        d.addBoth(self.storePerfStats, device)
        return d


    def storePerfStats(self, results, device):
        "Save the performance data in RRD files"
        if isinstance(results, failure.Failure):
            self.error(results)
            return results
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
        "Save an value in the right path in RRD files"
        path = 'Devices/%s/os/processes/%s/%s' % (deviceName, pidName, statName)
        value = self.rrd.save(path, value, rrdType, min=min, max=max)

        thresholds = self._devices[deviceName].processes[pidName].thresholds
        for t in thresholds.get(statName,[]):
            t.check(deviceName, pidName, statName, value,
                    self.sendThresholdEvent)
            

    def heartbeat(self, *unused):
        self.scanning = None
        devices = self.devices()
        pids = sum(map(lambda x: len(x.pids), devices.values()))
        log.info("Pulled process status for %d devices and %d processes",
                 len(devices), pids)
        SnmpDaemon.heartbeat(self)


    def main(self):
        self.sendEvent(self.startevt)
        drive(self.start).addCallbacks(self.periodic, self.errorStop)
        reactor.run(installSignalHandlers=False)
        self.sendEvent(self.stopevt, now=True)


if __name__ == '__main__':
    z = zenprocess()
    z.main()
