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

class Process:
    'track process-specific configuration data'
    name = None
    value = None
    count = None
    restart = None

    def match(self, name):
        if self.name is None:
            return False
        return self.value == name

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
        for name, value, count, restart in processes:
            unused.discard(name)
            p = self.processes.setdefault(name, Process())
            p.name = name
            p.value = value
            p.count = count
            p.restart = restart
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

            yield self.model.callRemote('getOSProcessConf')
            driver.next()

        return drive(doFetchConfig)

    def start(self, driver):
      try:
        # read config, find changes
        yield self.fetchConfig();
        n = driver.next()
        removed = Set(self.devices.keys())
        for (name, _, addr, (community, version, timeout, tries)), procs in n:
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
        for r in removed:
            del self.devices[r]

        # fetch pids with an SNMP scan
        yield self.findPids(); driver.next()
        driveLater(self.configCycleInterval * 60, self.start)
      except Exception, ex:
          import traceback
          traceback.print_exc(ex)

    def findPids(self):
        jobs = NJobs(PARALLEL_JOBS, self.scanDevice, self.devices.values())
        return jobs.start()

    def scanDevice(self, device):
        tables = [NAMETABLE, ARGSTABLE]
        d = device.getTables(tables)
        d.addCallback(self.storeProcessNames, device)
        d.addErrback(self.deviceFailure, device)
        return d

    def deviceFailure(self, value, device):
        from StringIO import StringIO
        s = StringIO()
        value.printTraceback(s)
        log.error('Error on device %s: %s', device, s.getvalue())

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
                    log.debug("Found process %d on %s" % (pid, p.name))
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
                                 self.fetchDevicePerf, self.devices.values())
        self.periodicJob.start().addCallback(self.heartbeat)
        reactor.callLater(self.snmpCycleInterval, self.periodic)

    def fetchDevicePerf(self, device):
        oids = []
        for p in device.pids.keys():
            oids.extend([CPU + str(p), MEM + str(p)])
        d = device.get(oids)
        d.addCallback(self.storePerfStats, device)
        d.addErrback(self.error)
        return d

    def storePerfStats(self, results, device):
        for pid, pidConf in device.pids.items():
            pidName = pidConf.name
            cpu = results.get(CPU + str(pid), None)
            mem = results.get(MEM + str(pid), None)
            if cpu is not None and mem is not None:
                self.save(device.name, pidName, 'cpu', cpu, 'COUNTER')
                self.save(device.name, pidName, 'mem', mem * 1024, 'GAUGE')

    def save(self, deviceName, pidName, statName, value, rrdType):
        path = 'Devices/%s/os/processes/%s/%s' % (deviceName, pidName, statName)
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
