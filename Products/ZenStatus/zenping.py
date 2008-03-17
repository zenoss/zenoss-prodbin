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


__doc__=''' ZenPing

Determines the availability of an IP address using ping.

$Id$'''

from socket import gethostbyname, getfqdn, gaierror

import time

import Globals # make zope imports work

from Products.ZenStatus.AsyncPing import Ping
from Products.ZenStatus.TestPing import Ping as TestPing
from Products.ZenStatus import pingtree
from Products.ZenUtils.Utils import unused
unused(pingtree)                        # needed for pb

from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.Driver import drive, driveLater

from twisted.internet import reactor

class ZenPing(PBDaemon):

    name = agent = "zenping"
    eventGroup = "Ping"
    initialServices = PBDaemon.initialServices + ['PingConfig']

    pingTimeOut = 1.5
    pingTries = 2
    pingChunk = 75
    pingCycleInterval = 60
    configCycleInterval = 20*60
    maxPingFailures = 2

    pinger = None
    pingTreeIter = None
    startTime = None
    jobs = 0
    reconfigured = True
    loadingConfig = None

    def __init__(self):
        PBDaemon.__init__(self, keeproot=True)
        if not self.options.useFileDescriptor:
            self.openPrivilegedPort('--ping')
        self.rrdStats = DaemonStats()
        if self.options.test:
            self.pinger = TestPing(self.pingTries, self.pingTimeOut)
        else:
            fd = None
            if self.options.useFileDescriptor is not None:
                fd = int(self.options.useFileDescriptor)
            self.pinger = Ping(self.pingTries, self.pingTimeOut, fd)
        self.log.info("started")


    def config(self):
        return self.services.get('PingConfig', FakeRemote())

    def stopOnError(self, error):
        self.log.exception(error)
        self.stop()
        return error

    def connected(self):
        self.log.debug("Connected, getting config")
        d = drive(self.loadConfig)
        d.addCallback(self.pingCycle)
        d.addErrback(self.stopOnError)

    def sendPingEvent(self, pj):
        "Send an event based on a ping job to the event backend."
        evt = dict(device=pj.hostname, 
                   ipAddress=pj.ipaddr, 
                   summary=pj.message, 
                   severity=pj.severity,
                   eventClass=Status_Ping,
                   eventGroup=self.eventGroup, 
                   agent=self.agent, 
                   component='',
                   manager=self.options.monitor)
        evstate = getattr(pj, 'eventState', None)
        if evstate is not None:
            evt['eventState'] = evstate
        self.sendEvent(evt)

    def loadConfig(self, driver):
        "Get the configuration for zenpin"

        if self.loadingConfig:
            self.log.warning("Configuration still loading.  Started at %s" %
                             time.strftime('%x %X', self.loadingConfig))
            return
        
        self.loadingConfig = time.time()

        self.log.info('fetching monitor properties')
        yield self.config().callRemote('propertyItems')
        items = dict(driver.next())
        for att in ("pingTimeOut",
                    "pingTries",
                    "pingChunk",
                    "pingCycleInterval",
                    "configCycleInterval",
                    "maxPingFailures",
                    ):
            before = getattr(self, att)
            after = items.get(att, before)
            setattr(self, att, after)
        self.configCycleInterval *= 60
        self.reconfigured = True

        driveLater(self.configCycleInterval, self.loadConfig)

        self.log.info("fetching default RRDCreateCommand")
        yield self.config().callRemote('getDefaultRRDCreateCommand')
        createCommand = driver.next()

        self.log.info("getting threshold classes")
        yield self.config().callRemote('getThresholdClasses')
        self.remote_updateThresholdClasses(driver.next())
        
        self.log.info("getting collector thresholds")
        yield self.config().callRemote('getCollectorThresholds')
        self.rrdStats.config(self.options.monitor,
                             self.name,
                             driver.next(), 
                             createCommand)

        self.log.info("getting ping tree")
        yield self.config().callRemote('getPingTree',
                                       self.options.name,
                                       findIp())
        self.pingtree = driver.next()

        self.rrdStats.gauge('configTime',
                            self.configCycleInterval,
                            time.time() - self.loadingConfig)
        self.loadingConfig = None


    def buildOptions(self):
        PBDaemon.buildOptions(self)
        self.parser.add_option('--name',
                               dest='name',
                               default=getfqdn(),
                               help=("host that roots the ping dependency "
                                     "tree: typically the collecting hosts' "
                                     "name; defaults to our fully qualified "
                                     "domain name (%s)" % getfqdn()))
        self.parser.add_option('--test',
                               dest='test',
                               default=False,
                               action="store_true",
                               help="Run in test mode: doesn't really ping,"
                               " but reads the list of IP Addresses that "
                               " are up from /tmp/testping")
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor',
                               default=None,
                               help=
                               "use the given (privileged) file descriptor")


    def pingCycle(self, unused=None):
        "Start a new run against the ping job tree"
        if self.options.cycle:
            reactor.callLater(self.pingCycleInterval, self.pingCycle)

        if self.pingTreeIter == None:
            self.start = time.time()
            self.jobs = 0
            self.pingTreeIter = self.pingtree.pjgen()
        while self.pinger.jobCount() < self.pingChunk and self.startOne():
            pass


    def startOne(self):
        "Initiate the next ping job"
        if not self.pingTreeIter:
            return False
        while 1:
            try:
                pj = self.pingTreeIter.next()
                if pj.status < self.maxPingFailures or self.reconfigured:
                    self.ping(pj)
                    return True
            except StopIteration:
                self.pingTreeIter = None
                return False

    def ping(self, pj):
        "Perform a ping"
        self.log.debug("starting %s", pj.ipaddr)
        pj.reset()
        self.pinger.sendPacket(pj)
        pj.deferred.addCallbacks(self.pingSuccess, self.pingFailed)
        
    def next(self):
        "Pull up the next ping job, which may throw StopIteration"
        self.jobs += 1
        self.startOne()
        if self.pinger.jobCount() == 0:
            self.endCycle()

    
    def endCycle(self, *unused):
        "Note the end of the ping list with a successful status message"
        runtime = time.time() - self.start
        self.log.info("Finished pinging %d jobs in %.2f seconds",
                      self.jobs, runtime)
        self.reconfigured = False
        if not self.options.cycle:
            reactor.stop()
        else:
            self.heartbeat()

    def heartbeat(self):
        'Send a heartbeat event for this monitor.'
        PBDaemon.heartbeat(self)
        for ev in (self.rrdStats.gauge('cycleTime',
                                       self.pingCycleInterval,
                                       time.time() - self.start) +
                   self.rrdStats.gauge('devices',
                                       self.pingCycleInterval,
                                       self.jobs)):
            self.sendEvent(ev)

    def pingSuccess(self, pj):
        "Callback for a good ping response"
        pj.deferred = None
        if pj.status > 1:
            pj.severity = 0
            self.sendPingEvent(pj)
        self.log.debug("Success %s", pj.ipaddr)
        pj.status = 0
        self.next()

    def pingFailed(self, err):
        try:
            self.doPingFailed(err)
        except Exception, ex:
            import traceback
            from StringIO import StringIO
            out = StringIO()
            traceback.print_exc(ex, out)
            self.log.error("Exception: %s", out.getvalue())

    def doPingFailed(self, err):
        "Callback for a bad (no) ping response"
        pj = err.value
        pj.deferred = None
        pj.status += 1
        self.log.debug("Failed %s %s", pj.ipaddr, pj.status)
        if pj.status == 1:         
            self.log.debug("first failure '%s'", pj.hostname)
            # if our path back is currently clear add our parent
            # to the ping list again to see if path is really clear
            # and then re-ping ourself.
            if not pj.checkpath():
                routerpj = pj.routerpj()
                if routerpj:
                    self.ping(routerpj)
                self.ping(pj)
        else:
            failname = pj.checkpath()
            if failname:
                pj.eventState = 2 # suppressed FIXME
                pj.message += (", failed at %s" % failname)
            self.log.warn(pj.message)
            self.sendPingEvent(pj)
            self.markChildrenDown(pj)
        
        self.next()

    def markChildrenDown(self, pj):
        """If this is a router PingJob, mark all Nodes
        away from the ping monitor as down"""

        # unfortunately there's no mapping from pj to router, so find it
        routers = []
        def recurse(node):
            if routers: return
            if node.pj == pj:
                routers.append(node)
            for c in node.children:
                recurse(c)
        recurse(self.pingtree)
        if not routers: return
        assert len(routers) == 1
        children = routers[0].pjgen()
        children.next()                 # skip self
        for pj in children:
            pj.eventState = 2           # suppress
            self.sendPingEvent(pj)


    def remote_updateConfig(self):
        self.log.debug("Asynch update config")
        if self.loadingConfig:
            return
        d = drive(self.loadConfig)
        def reportError(result):
            self.log.error("Error loading config: %s" % result)
        d.addErrback(reportError)

    def remote_deleteDevice(self, device):
        self.log.debug("Asynch delete device %s" % device)
        self.remote_updateConfig()
        

def findIp():
    try:
        return gethostbyname(getfqdn())
    except gaierror:
        # find the first non-loopback interface address
        import os
        import re
        ifconfigs = ['/sbin/ifconfig',
                     '/usr/sbin/ifconfig',
                     '/usr/bin/ifconfig',
                     '/bin/ifconfig']
        ifconfig = filter(os.path.exists, ifconfigs)[0]
        fp = os.popen(ifconfig + ' -a')
        config = fp.read().split('\n\n')
        fp.close()
        digits = r'[0-9]{1,3}'
        pat = r'(addr:|inet) *(%s\.%s\.%s\.%s)[^0-9]' % ((digits,)*4)
        parse = re.compile(pat)
        results = []
        for c in config:
            addr = parse.search(c)
            if addr:
                results.append(addr.group(2))
        try:
            results.remove('127.0.0.1')
        except ValueError:
            pass
        if results:
            return results[0]
    return '127.0.0.1'

if __name__=='__main__':
    pm = ZenPing()
    import logging
    logging.getLogger('zen.Events').setLevel(20)
    pm.run()
