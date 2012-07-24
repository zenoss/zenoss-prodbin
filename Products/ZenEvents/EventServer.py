##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''EventServer

Base class for ZenSyslog, ZenTrap and others

$Id$
'''

__version__ = "$Revision$"[11:-2]

import socket

import Globals

from Products.ZenHub.PBDaemon import PBDaemon, FakeRemote
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.Driver import drive

from Products.ZenEvents.ZenEventClasses import App_Start
from twisted.internet import reactor

import time

class Stats:
    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    
    def add(self, moreTime):
        self.totalEvents += 1
        self.totalTime += moreTime
        self.maxTime = max(self.maxTime, moreTime)

    def report(self):
        return self.totalTime, self.totalEvents, self.maxTime

class EventServer(PBDaemon):
    'Base class for a daemon whose primary job is to post events'

    name = 'EventServer'
    
    def __init__(self):
        PBDaemon.__init__(self, keeproot=True)
        self.stats = Stats()
        self.rrdStats = DaemonStats()


    def connected(self):
        self.sendEvent(dict(device=self.options.monitor, 
                            eventClass=App_Start, 
                            summary="%s started" % self.name,
                            severity=0,
                            component=self.name))
        self.log.info("started")
        self.configure()


    def model(self):
        return self.services.get('EventService', FakeRemote())


    def configure(self):
        def inner(driver):
            self.log.info("fetching default RRDCreateCommand")
            yield self.model().callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()
        
            self.log.info("getting threshold classes")
            yield self.model().callRemote('getThresholdClasses')
            self.remote_updateThresholdClasses(driver.next())
        
            self.log.info("getting collector thresholds")
            yield self.model().callRemote('getCollectorThresholds')
            self.rrdStats.config(self.options.monitor, self.name,
                                 driver.next(), createCommand)
            self.heartbeat()
            self.reportCycle()
        d = drive(inner)
        def error(result):
            self.log.error("Unexpected error in configure: %s" % result)
        d.addErrback(error)
        return d


    def sendEvent(self, event, **kw):
        # FIXME: get real event processing stats
        if 'firstTime' in event:
            self.stats.add(min(time.time() - event['firstTime'], 0))
        PBDaemon.sendEvent(self, event, **kw)


    def useUdpFileDescriptor(self, fd):
        from twisted.internet import udp
        s = socket.fromfd(fd, socket.AF_INET, socket.SOCK_DGRAM)
        import os
        os.close(fd)
        port = s.getsockname()[1]
        transport = udp.Port(port, self)
        s.setblocking(0)
        transport.socket = s
        transport.fileno = s.fileno
        transport.connected = 1
        transport._realPortNumber = port
        self.transport = transport
        # hack around startListening not being called
        self.numPorts = 1
        transport.startReading()


    def useTcpFileDescriptor(self, fd, factory):
        import os, socket
        for i in range(19800, 19999):
            try:
                p = reactor.listenTCP(i, factory)
                os.dup2(fd, p.socket.fileno())
                p.socket.listen(p.backlog)
                p.socket.setblocking(False)
                p.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                os.close(fd)
                return p
            except socket.error:
                pass
        raise socket.error("Unable to find an open socket to listen on")


    def reportCycle(self):
        if self.options.statcycle:
            self.report()
            reactor.callLater(self.options.statcycle, self.reportCycle)


    def heartbeat(self):
        """Since we don't do anything on a regular basis, just
        push heartbeats regularly"""
        seconds = self.heartbeatTimeout / 3
        reactor.callLater(self.heartbeatTimeout / 3, self.heartbeat)
        PBDaemon.heartbeat(self)
        totalTime, totalEvents, maxTime = self.stats.report()
        for ev in (self.rrdStats.counter('events',
                                         seconds,
                                         totalEvents) +
                   self.rrdStats.counter('totalTime',
                                         seconds,
                                         int(totalTime * 1000))):
            self.sendEvent(ev)

        
    def report(self):
        'report some simple diagnostics at shutdown'
        totalTime, totalEvents, maxTime = self.stats.report()
        self.log.info("%d events processed in %.2f seconds",
                      totalEvents,
                      totalTime)
        if totalEvents > 0:
            self.log.info("%.5f average seconds per event",
                       (totalTime / totalEvents))
            self.log.info("Maximum processing time for one event was %.5f",
                          maxTime)


    def buildOptions(self):
        PBDaemon.buildOptions(self)
        self.parser.add_option('--statcycle',
                               dest='statcycle',
                               type='int',
                               help='Number of seconds between the writing of statistics',
                               default=0)
