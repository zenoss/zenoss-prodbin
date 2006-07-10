#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''EventServer

Base class for ZenXEvent and ZenTrap

$Id$
'''

__version__ = "$Revision$"[11:-2]

from twisted.python import threadable
threadable.init()

from Queue import Queue

import time
import socket

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase

from Event import Event, EventHeartbeat

from ZenEventClasses import AppStart, AppStop
from twisted.internet import reactor, defer

class EventServer(ZCmdBase):
    'Listen for xmlrpc requests and turn them into events'

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.
    name = 'EventServer'

    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        
        self.zem = self.dmd.ZenEventManager
        self.sendEvent(Event(device=socket.getfqdn(), 
                               eventClass=AppStart, 
                               summary="%s started" % self.name,
                               severity=0,
                               component=self.name))
        self.q = Queue()
        self.log.info("started")
        self.heartbeat()


    def run(self):
        'method to process events in a thread'
        while 1:
            args = self.q.get()
            if args is None:
                break
            if isinstance(args, Event):
                self.sendEvent(args)
            else:
                self.doHandleRequest(*args)
                diff = time.time() - args[-1]
                self.totalTime += diff
                self.totalEvents += 1
                self.maxTime = max(diff, self.maxTime)
            self.syncdb()

    def sendEvent(self, evt):
        "wrapper for sending an event"
        self.zem.sendEvent(evt)


    def heartbeat(self):
        """Since we don't do anything on a regular basis, just
        push heartbeats regularly"""
        seconds = 10
        evt = EventHeartbeat(socket.getfqdn(), self.name, 3*seconds)
        self.q.put(evt)
        reactor.callLater(seconds, self.heartbeat)

        
    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()

    def report(self):
        'report some simple diagnostics at shutdown'
        self.log.info("%d events processed in %.2f seconds",
                   self.totalEvents,
                   self.totalTime)
        if self.totalEvents > 0:
            self.log.info("%.5f average seconds per event",
                       (self.totalTime / self.totalEvents))
            self.log.info("Maximum processing time for one event was %.5f",
                          self.maxTime)

    def finish(self):
        'things to do at shutdown: thread cleanup, logs and events'
        self.q.put(None)
        self.report()
        self.sendEvent(Event(device=socket.getfqdn(), 
                             eventClass=AppStop, 
                             summary="%s stopped" % self.name,
                             severity=4,
                             component=self.name))

    def main(self):
        reactor.callInThread(self.run)
        reactor.addSystemEventTrigger('before', 'shutdown', self.finish)
        reactor.run(installSignalHandlers=False)
        
