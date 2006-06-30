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
import socket
from sets import Set

log = logging.getLogger("zen.zenprocess")

from twisted.internet import reactor, defer

from twistedsnmp.agentproxy import AgentProxy
from twistedsnmp.tableretriever import TableRetriever
from twistedsnmp import snmpprotocol

import Globals
from Products.ZenUtils.ZenDaemon import ZenDaemon
from Products.ZenUtils.Driver import drive
from Products.ZenUtils.NJobs import NJobs
from Products.ZenUtils.Utils import basicAuthUrl
from Products.ZenUtils.TwistedAuth import AuthProxy
from Products.ZenEvents import Event
from Products.ZenModel.PerformanceConf import performancePath

import RRDUtil

BAD_SEVERITY=Event.Warning

HOSTROOT  ='.1.3.6.1.2.1.25'
RUNROOT   = HOSTROOT + '.4'
NAMETABLE = RUNROOT + '.2.1.4'
ARGSTABLE = RUNROOT + '.2.1.5'
PERFROOT  = HOSTROOT + '.5'
CPU       = PERFROOT + '.1.1.1.'        # note trailing dot
MEM       = PERFROOT + '.1.1.2.'        # note trailing dot

BASE_URL = 'http://localhost:8080/zport/dmd'
DEFAULT_URL = BASE_URL + '/Monitors/StatusMonitors/localhost'

PARALLEL_JOBS = 10
MAX_OIDS_PER_REQUEST = 40

COMMON_EVENT_INFO = {
    'agent': 'zenprocess',
    'manager': socket.getfqdn(),
    }

try:
    sorted = sorted
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

class zenprocess(ZenDaemon):
    startevt = {'device':socket.getfqdn(), 'eventClass':'/App/Start', 
                'component':'zenperfsnmp', 'summary': 'started',
                'severity': Event.Clear}
    stopevt = {'device':socket.getfqdn(), 'eventClass':'/App/Stop', 
               'component':'zenperfsnmp', 'summary': 'stopped',
               'severity': BAD_SEVERITY}
    heartbeat = {'device':socket.getfqdn(), 'component':'zenperfsnmp',
                    'eventClass':'/Heartbeat'}

    snmpCycleInterval = 5*60
    configCycleInterval = 20
    rrd = None

    def __init__(self):
        ZenDaemon.__init__(self)
        self.devices = {}
        self.snmpPort = snmpprotocol.port()
        self.periodicJob = None
        self.model = self.buildProxy(self.options.zopeurl)
        baseURL = '/'.join(self.options.zopeurl.rstrip('/').split('/')[:-2])
        if not self.options.zem:
            self.options.zem = baseURL + '/ZenEventManager'
        self.zem = self.buildProxy(self.options.zem)
        self.events = []

    def buildProxy(self, url):
        "create AuthProxy objects with our config and the given url"
        url = basicAuthUrl(self.options.zopeusername,
                           self.options.zopepassword,
                           url)
        return AuthProxy(url)


    def sendEvent(self, event, now=False, **kw):
        'convenience function for pushing events to the Zope server'
        ev = event.copy()
        ev.update(COMMON_EVENT_INFO)
        ev.update(kw)
        self.events.append(ev)
	if now:
	    self.sendEvents()


    def sendEvents(self):
        if self.events:
            d = self.zem.callRemote('sendEvents', self.events)
            d.addErrback(self.log.error)
            self.events = []

    def fetchConfig(self):
        'Get configuration values from the Zope server'
        def doFetchConfig(driver):
            yield self.model.callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()

            yield self.model.callRemote('propertyItems')
            table = dict(driver.next())
            for name in ('configCycleInterval', 'snmpCycleInterval'):
                if table.has_key(name):
                    value = table[name]
                    if getattr(self, name) != value:
                        self.log.debug('Updated %s config to %s' % (name, value))
                    setattr(self, name, value)
            self.rrd = RRDUtil.RRDUtil(createCommand, self.snmpCycleInterval)

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
        reactor.callLater(self.configCycleInterval * 60, self.restart)

    def restart(self):
        drive(self.start)

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
        
    def periodic(self, ignored=None):
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
        path = '%s/%s/%s/%d.rrd' % (deviceName, pidName, statName, pid)
        value = self.rrd.save(path, value, rrdType)
        # fixme: add threshold checking
            

    def heartbeat(self, *unused):
        if not self.options.cycle:
            reactor.stop()
            return
        self.periodicJob = None
        pids = sum(map(lambda x: len(x.pids), self.devices.values()))
        log.debug("Pulled config for %d devices and %d processes",
                  len(self.devices), pids)

    def error(self, err):
        print err.printTraceback()
        import traceback
        traceback.print_exc(err.value)
        reactor.callLater(0, reactor.stop)

    def sigTerm(self, *unused):
        'controlled shutdown of main loop on interrupt'
        try:
            ZenDaemon.sigTerm(self, *unused)
        except SystemExit, ex:
            reactor.stop()

    def main(self):
        self.sendEvent(self.startevt)
        drive(self.start).addCallbacks(self.periodic, self.error)
        reactor.run(installSignalHandlers=False)
        self.sendEvent(self.stopevt, now=True)

    def buildOptions(self):
        ZenDaemon.buildOptions(self)
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
        self.parser.add_option(
            '--zem', dest='zem',
            help="XMLRPC path to an ZenEventManager instance")

if __name__ == '__main__':
    z = zenprocess()
    z.main()
