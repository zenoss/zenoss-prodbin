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

__doc__='''EventServer

Base class for ZenXEvent and ZenTrap

$Id$
'''

__version__ = "$Revision$"[11:-2]

from twisted.python import threadable
threadable.init()

from Queue import Queue
from threading import Lock
import time
import socket

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.DaemonStats import DaemonStats

from Event import Event, EventHeartbeat

from ZenEventClasses import App_Start, App_Stop
from twisted.internet import reactor

class Stats:
    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    
    def __init__(self):
        self.lock = Lock()
    
    def add(self, moreTime):
        self.lock.acquire()
        self.totalEvents += 1
        self.totalTime += moreTime
        self.maxTime = max(self.maxTime, moreTime)
        self.lock.release()

    def report(self):
        try:
            self.lock.acquire()
            return self.totalTime, self.totalEvents, self.maxTime
        finally:
            self.lock.release()

class EventServer(ZCmdBase):
    'Base class for a daemon whose primary job is to post events'

    name = 'EventServer'
    
    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        self.stats = Stats()
        self.zem = self.dmd.ZenEventManager
        self.sendEvent(Event(device=self.options.monitor, 
                               eventClass=App_Start, 
                               summary="%s started" % self.name,
                               severity=0,
                               component=self.name))
        self.q = Queue()
        self.log.info("started")
    
        self.rrdStats = DaemonStats()
        monitor = self.dmd.Monitors.Performance._getOb(self.options.monitor)
        self.rrdStats.configWithMonitor(self.name, monitor)
        self.reportCycle()

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

    def run(self):
        'method to process events in a thread'
        try:
            while 1:
                args = self.q.get()
                if args is None:
                    break
                try:
                    if isinstance(args, Event):
                        self.sendEvent(args)
                    else:
                        self.doHandleRequest(*args)
                        diff = time.time() - args[-1]
                        self.stats.add(diff)
                except Exception, ex:
                    self.log.exception(ex)
                self.syncdb()
        finally:
            if reactor.running:
                reactor.stop()


    def sendEvent(self, evt, **kw):
        "wrapper for sending an event"
        self.zem._p_jar.sync()
        if type(evt) == dict:
            evt['manager'] = self.options.monitor
            evt.update(kw)
        else:
            evt.manager = self.options.monitor
            evt.__dict__.update(kw)
        self.zem.sendEvent(evt)


    def sendEvents(self, evts):
        """Send multiple events to database syncing only one time.
        """
        self.zem._p_jar.sync()
        for e in evts:
            self.zem.sendEvent(e)


    def heartbeat(self):
        """Since we don't do anything on a regular basis, just
        push heartbeats regularly"""
        seconds = 60
        evt = EventHeartbeat(self.options.monitor, self.name, 3*seconds)
        self.q.put(evt)
        self.niceDoggie(seconds)
        reactor.callLater(seconds, self.heartbeat)
        totalTime, totalEvents, maxTime = self.stats.report()
        for ev in (self.rrdStats.counter('events',
                                         seconds,
                                         totalEvents) +
                   self.rrdStats.counter('totalTime',
                                         seconds,
                                         int(totalTime * 1000)) +
                   self.rrdStats.gauge('qsize',
                                       seconds,
                                       self.q.qsize())):
            self.sendEvent(**ev)

        
    def sigTerm(self, signum=None, frame=None):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            if reactor.running:
                reactor.stop()

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

    def finish(self):
        'things to do at shutdown: thread cleanup, logs and events'
        self.q.put(None)
        self.report()
        self.sendEvent(Event(device=self.options.monitor, 
                             eventClass=App_Stop, 
                             summary="%s stopped" % self.name,
                             severity=4,
                             component=self.name))

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--statcycle',
                               dest='statcycle',
                               type='int',
                               help='Number of seconds between the writing of statistics',
                               default=0)
        self.parser.add_option(
            '--monitor',
            dest='monitor',
            help='Name of the distributed monitor running this event generator',
            default='localhost')

    def _wakeUpReactorAndHandleSignals(self):
        reactor.callLater(1.0, self._wakeUpReactorAndHandleSignals)
        
    def main(self):
        reactor.callInThread(self.run)
        reactor.addSystemEventTrigger('before', 'shutdown', self.finish)
        self._wakeUpReactorAndHandleSignals()
        reactor.run()
        
