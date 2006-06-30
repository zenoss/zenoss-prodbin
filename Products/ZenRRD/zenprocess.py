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

import re
import logging
from sets import Set

log = logging.getLogger("zen.zenprocess")

from twisted.internet import reactor, defer

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp.tableretriever import TableRetriever

import Globals
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.NJobs import NJobs
from Products.ZenModel.PerformanceConf import performancePath

from RRDUtil import RRDUtil
from RRDDaemon import RRDDaemon

HOSTROOT  ='.1.3.6.1.2.1.25'
RUNROOT   = HOSTROOT + '.4'
NAMETABLE = RUNROOT + '.2.1.4'
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

class Process:
    'track process-specific configuration data'
    name = None
    pattern = None

    def match(self, name):
        if self.name is None:
            return False
        return re.match(self.pattern, name)

class Device:
    'track device data'
    name = ''
    address = ('', 0)
    community = 'public'
    version = '2'
    port = 161
    proxy = None

    def __init__(self):
        # map process name to Process object above
        self.processes = {}
        # map pid number to Process object
        self.pids = {}

    def makeProxy(self, protocol):
        p = self.proxy
        if (p is None or 
            (p.ip, p.port) != self.address or
            p.snmpVersion != self.version or
            p.port != self.port):
            self.proxy = AgentProxy(ip=self.address[0],
                                    port=self.address[1],
                                    community=self.community,
                                    snmpVersion=self.version,
                                    protocol=protocol,
                                    allowCache=True)

    
    def updateConfig(self, processes):
        unused = Set(self.processes.keys())
        for name, pattern in processes:
            unused.discard(name)
            p = self.processes.setdefault(name, Process())
            p.name = name
            p.pattern = pattern
        for name in unused:
            del self.processes[name]

config = [
    ('mysql', '.*/mysqld_safe.*'),
    ('zenoss', '.*python.*zdrun.py.*runzope'),
    ]

devices = [ ('eros', ('192.168.1.120', 161), 'public', config) ]

class zenprocess(RRDDaemon):

    def __init__(self):
        RRDDaemon.__init__(self, 'zenprocess')
        self.devices = {}
        self.periodicJob = None

    def fetchConfig(self):
        'Get configuration values from the Zope server'
        def doFetchConfig(driver):
            yield self.model.callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()

            yield self.model.callRemote('propertyItems')
            self.setPropertyItems(driver.next())
            
            self.rrd = RRDUtil(createCommand, self.snmpCycleInterval)
            
            yield defer.succeed(devices)
            driver.next()
        
        return drive(doFetchConfig)

    def start(self, driver):
        # read config, find changes
        yield self.fetchConfig();
        n = driver.next()
        removed = Set(self.devices.keys())
        for name, addr, community, cfg in n:
            removed.discard(name)
            d = self.devices.setdefault(name, Device())
            d.name = name
            d.address = addr
            d.community = community
            d.updateConfig(cfg)
            d.makeProxy(self.snmpPort.protocol)
        for r in removed:
            del self.devices[r]

        # fetch pids with an SNMP scan
        yield self.findPids(); driver.next()
        driveLater(self.configCycleInterval * 60, self.start)

    def findPids(self):
        jobs = NJobs(PARALLEL_JOBS, self.scanDevice, self.devices.values())
        return jobs.start()

    def scanDevice(self, device):
        tables = [NAMETABLE, ARGSTABLE]
        t = TableRetriever(device.proxy, tables,
                           maxRepetitions=MAX_OIDS_PER_REQUEST / len(tables))
        d = t()
        d.addCallback(self.storeProcessNames, device)
        d.addErrback(self.deviceFailure, device)
        return d

    def deviceFailure(self, value, device):
        value.printTraceback()
        log.error('Error: %s %s', value, device)

    def storeProcessNames(self, results, device):
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
                    after[pid] = p
        afterSet = Set(after.keys())
        new =  afterSet - before
        dead = before - afterSet
        # report changes
        for p in new:
            name = after[p].name
            log.debug("Found new %s pid %d on %s" % (name, p, device.name))
        for p in dead:
            name = device.pids[p].name
            log.debug("Process %s pid %d now gone on %s" % (name, p, device.name))
        device.pids = after
        
    def periodic(self, unused=None):
        if self.periodicJob:
            running, unstarted, finished = self.periodicJob.status()
            log.error("periodic job not finishing: "
                      "%d jobs running %d jobs waiting %d jobs finished",
                      running, unstarted, finished)
            return
        # in M-parallel, for each device
        # fetch the process status
        self.periodicJob = NJobs(MAX_OIDS_PER_REQUEST,
                                 self.fetchDevice, self.devices.values())
        self.periodicJob.start().addCallback(self.heartbeat)
        reactor.callLater(self.snmpCycleInterval, self.periodic)

    def fetchDevice(self, device):
        oids = []
        for p in device.pids.keys():
            oids.extend([CPU + str(p), MEM + str(p)])
        d = device.proxy.get(oids)
        d.addCallback(self.storeStats, device)
        d.addErrback(self.error)
        return d

    def storeStats(self, results, device):
        for pid, pidConf in device.pids.items():
            pidName = pidConf.name
            cpu = results.get(CPU + str(pid), None)
            mem = results.get(CPU + str(pid), None)
            if cpu is not None and mem is not None:
                self.save(device.name, pidName, 'cpu', cpu, pid, 'COUNTER')
                self.save(device.name, pidName, 'mem', mem, pid, 'GAUGE')

    def save(self, deviceName, pidName, statName, value, pid, rrdType):
        path = '%s/processes/%s/%s/%d' % (deviceName, pidName, statName, pid)
        value = self.rrd.save(path, value, rrdType)
        # fixme: add threshold checking
            

    def heartbeat(self, *unused):
        self.periodicJob = None
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
