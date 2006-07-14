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

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp.tableretriever import TableRetriever

import Globals
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.NJobs import NJobs
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenEvents import Event

from RRDUtil import RRDUtil
from RRDDaemon import RRDDaemon, Threshold

HOSTROOT  ='.1.3.6.1.2.1.25'
RUNROOT   = HOSTROOT + '.4'
NAMETABLE = RUNROOT + '.2.1.2'
ARGSTABLE = RUNROOT + '.2.1.5'
PERFROOT  = HOSTROOT + '.5'
CPU       = PERFROOT + '.1.1.1.'        # note trailing dot
MEM       = PERFROOT + '.1.1.2.'        # note trailing dot

PARALLEL_JOBS = 10
MAX_OIDS_PER_REQUEST = 40

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

class ScanFailure(Exception): pass

class Process:
    'track process-specific configuration data'
    name = None
    originalName = None
    count = None
    restart = None
    severity = Event.Warning
    status = 0

    def match(self, name):
        if self.name is None:
            return False
        return self.originalName == name

    def __str__(self):
        return str(self.name)
    __repr__ = __str__

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

    
    def updateConfig(self, processes):
        unused = Set(self.processes.keys())
        for name, originalName, count, restart, severity, status, thresholds \
                in processes:
            unused.discard(name)
            p = self.processes.setdefault(name, Process())
            p.name = name
            p.originalName = originalName
            p.count = count
            p.restart = restart
            p.severity = severity
            for t in thresholds:
                print 'threshold for ', name, t
            p.thresholds = dict(
               [(name, Threshold(*t)) for name, t in thresholds]
            )
            p.status = status
        for name in unused:
            del self.processes[name]

    def get(self, oids):
        self._makeProxy()
        return self.proxy.get(oids,
                              timeout=self.timeout,
                              retryCount=self.tries)


    def getTables(self, oids):
        self._makeProxy()
        t = TableRetriever(self.proxy, oids,
                           timeout=self.timeout,
                           retryCount=self.tries,
                           maxRepetitions=MAX_OIDS_PER_REQUEST / len(oids))
        return t()

    def hasCountedProcess(self):
        for p in self.processes:
            if p.count:
                return True
        return False
    

class zenprocess(RRDDaemon):
    statusEvent = { 'eventClass' : '/Status/OSProcess',
                    'eventGroup' : 'Process' }

    def __init__(self):
        RRDDaemon.__init__(self, 'zenprocess')
        self.devices = {}
        self.perfScanJob = None


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
        yield self.fetchConfig();
        n = driver.next()
        removed = Set(self.devices.keys())
        for (name, snmpStatus, addr, snmpConf), procs in n:
            community, version, timeout, tries = snmpConf
            removed.discard(name)
            d = self.devices.setdefault(name, Device())
            d.name = name
            d.address = addr
            d.community = community
            d.version = version
            d.timeout = timeout
            d.tries = tries
            d.updateConfig(procs)
            d.protocol = self.snmpPort.protocol
            d.snmpStatus = snmpStatus
        for r in removed:
            del self.devices[r]

        # fetch pids with an SNMP scan
        yield self.findPids(self.devices.values()); driver.next()
        driveLater(self.configCycleInterval * 60, self.start)


    def findPids(self, devices):
        "Scan all devices for process names and args"
        devices = [d for d in devices if d.snmpStatus <= 1]
        jobs = NJobs(PARALLEL_JOBS, self.scanDevice, devices)
        return jobs.start()


    def scanDevice(self, device):
        """Fetch all the process info, but not too often:
        
        Both 'counted' and 'config' cycles scan devices.

        """
        if time.time() - device.lastScan < self.snmpCycleInterval:
            return defer.succeed(None)
        tables = [NAMETABLE, ARGSTABLE]
        d = device.getTables(tables)
        d.addCallback(self.storeProcessNames, device)
        d.addErrback(self.deviceFailure, device)
        return d


    def deviceFailure(self, error, device):
        "Log exception for a single device"
        self.logError('Error on device %s' % device.name, error)


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
            
        device.lastScan = time.time()
        procs = []
        for namePart, argsPart in zip(sorted(results[NAMETABLE].items()),
                                      sorted(results[ARGSTABLE].items())):
            oid, name = namePart
            namepid = int(oid.split('.')[-1])
            oid, args = argsPart
            argpid = int(oid.split('.')[-1])
            if namepid == argpid:
                procs.append( (namepid, '%s %s' % (name, args)) )
        # look for changes in pids
        before = Set(device.pids.keys())
        after = {}
        for p in device.processes.values():
            for pid, running in procs:
                if p.match(running):
                    log.debug("Found process %d on %s" % (pid, p.name))
                    after[pid] = p
        afterSet = Set(after.keys())
        afterByConfig = reverseDict(after)
        new =  afterSet - before
        dead = before - afterSet

        # report pid restarts
        for p in dead:
            config = device.pids[p]
            if not config.count and afterByConfig.has_key(config):
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
            if pidConfig.count:
                pidCounts[pidConfig.name] += 1
        for name, count in pidCounts.items():
            self.save(device.name, name, 'count', count, 'GAUGE')


    def periodic(self, unused=None):
        "Basic SNMP scan loop"
        d = defer.DeferredList([self.perfScan(), self.countScan()],
                               consumeErrors=True)
        d.addCallback(self.heartbeat)
        reactor.callLater(self.snmpCycleInterval, self.periodic)


    def perfScan(self):
        "Read performance data for non-counted Processes"
        if self.perfScanJob:
            running, unstarted, finished = self.perfScanJob.status()
            msg = "performance scan job not finishing: " \
                  "%d jobs running %d jobs waiting %d jobs finished" % \
                  (running, unstarted, finished)
            log.error(msg)
            return defer.fail(ScanFailure(msg))
        # in M-parallel, for each device
        # fetch the process status
        self.perfScanJob = NJobs(MAX_OIDS_PER_REQUEST,
                                 self.fetchDevicePerf, self.devices.values())
        return self.perfScanJob.start()


    def countScan(self):
        "Read counts for counted Processes"
        devices = [d for d in self.devices.values() if d.hasCountedProcess()]
        return self.findPids(devices)


    def fetchDevicePerf(self, device):
        "Get performance data for all the monitored Processes on a device"
        oids = []
        for pid, pidConf in device.pids.items():
            if not pidConf.count:
                oids.extend([CPU + str(pid), MEM + str(pid)])
        if not oids:
            return defer.succeed(([], device))
        d = device.get(oids)
        d.addCallback(self.storePerfStats, device)
        d.addErrback(self.error)
        return d


    def storePerfStats(self, results, device):
        "Save the performance data in RRD files"
        byConf = reverseDict(device.pids)
        for pidConf, pids in byConf.items():
            if len(pids) != 1:
                log.warning("There are %d pids by the name %s",
                            len(pids), pidConf.name)
            pid = pids[0]
            pidName = pidConf.name
            cpu = results.get(CPU + str(pid), None)
            mem = results.get(MEM + str(pid), None)
            if cpu is not None and mem is not None:
                self.save(device.name, pidName, 'cpu', cpu, 'COUNTER')
                self.save(device.name, pidName, 'mem', mem * 1024, 'GAUGE')


    def save(self, deviceName, pidName, statName, value, rrdType):
        "Save an value in the right path in RRD files"
        path = 'Devices/%s/os/processes/%s/%s' % (deviceName, pidName, statName)
        value = self.rrd.save(path, value, rrdType)

        thresholds = self.devices[deviceName].processes[pidName].thresholds
        for t in thresholds.get(statName,[]):
            t.check(deviceName, pidName, statName, value,
                    self.sendThresholdEvent)
            

    def heartbeat(self, *unused):
        self.perfScanJob = None
        pids = sum(map(lambda x: len(x.pids), self.devices.values()))
        log.debug("Pulled process status for %d devices and %d processes",
                  len(self.devices), pids)
        RRDDaemon.heartbeat(self)


    def main(self):
        self.sendEvent(self.startevt)
        drive(self.start).addCallbacks(self.periodic, self.error)
        reactor.run(installSignalHandlers=False)
        self.sendEvent(self.stopevt, now=True)


if __name__ == '__main__':
    z = zenprocess()
    z.main()
