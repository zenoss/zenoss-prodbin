#!/usr/bin/env python2.1

#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__=''' ZenPing

creates a queue of hosts to be pinged (jobs),
and pings them until they respond, or the
maximum number of pings has been sent. After
sending out all these pings, we loop in a
receive function processing everything we get
back

$Id: ZenPing.py,v 1.70 2004/04/22 20:54:23 edahl Exp $'''

__version__ = "$Revision: 1.70 $"[11:-2]

import socket
import ip
import icmp
import os
import time
import select
import sys
import xmlrpclib
import Queue

import Globals # make zope imports work

from Products.ZenEvents.MySqlSendEvent import MySqlSendEventThread
from Products.ZenEvents.Event import Event
from Products.ZenEvents.ZenEventClasses import PingStatus
from Products.ZenUtils.Utils import parseconfig, basicAuthUrl
from Products.ZenUtils.ZCmdBase import ZCmdBase
from PingThread import PingThread
import pingtree


class ZenPing(ZCmdBase):

    agent = "ZenPing"
    eventGroup = "Ping"

    pathcheckthresh = 10

    copyattrs = (
        "timeOut",
        "tries",
        "chunk",
        "cycleInterval",
        "configCycleInterval",
        "maxFailures",
    )

    def __init__(self):
        ZCmdBase.__init__(self)
        self.hostname = socket.getfqdn()
        self.configpath = self.options.configpath
        if self.configpath.startswith("/"):
            self.configpath = self.configpath[1:]
        self.configCycleInterval = 0
        self.configTime = 0
        self.reportqueue = Queue.Queue()

        self.eventThread = MySqlSendEventThread(self.dmd.ZenEventManager)
        self.eventThread.start()
        self.log.info("started")


    def loadConfig(self):
        "get the config data from file or server"
        if time.time()-self.configTime > self.configCycleInterval:
            self.getDataRoot()
            self.syncdb()
            smc = self.dmd.unrestrictedTraverse(self.configpath)
            for att in self.copyattrs:
                value = getattr(smc, att)
                setattr(self, att, value)
            self.configCycleInterval = self.configCycleInterval*60
            me = None
            if self.options.name:
                me = self.dmd.Devices.findDevice(self.options.name)
                self.log.info("device %s not found trying %s", 
                              self.options.name, self.hostname)
            else:
                me = self.dmd.Devices.findDevice(self.hostname)
            if me: 
                self.log.info("building pingtree from %s", me.id)
                self.pingtree = pingtree.buildTree(me)
            else:
                self.log.critical("ZenPing '%s' not found,"
                                  "ignoring network topology.",self.hostname)
                ip = socket.gethostbyname(self.hostname)
                self.pingtree = pingtree.Rnode(ip, self.hostname, 0)
            devices = smc.getPingDevices()
            self.prepDevices(devices)
            self.configTime = time.time()
            self.closedb()


    def prepDevices(self, devices):
        """resolve dns names and make StatusTest objects"""
        for device in devices:
            status = device.getStatus(PingStatus)
            if status >= self.maxFailures:
                cycle = self.configCycleInterval
            else:
                cycle = self.cycleInterval
            self.log.debug("add device '%s' cycle=%s",device.id, cycle)
            self.pingtree.addDevice(device, cycle)


    def sendPing(self, pj):
        if pj.inprocess or pj.pathcheck > self.pathcheckthresh: return
        self.sent += 1
        pj.inprocess = True
        pj.pathcheck += 1
        self.log.debug("queue '%s' ip '%s'", pj.hostname, pj.ipaddr)
        self.pingThread.sendPing(pj)


    def receiveReport(self):
        try:
            pj = self.reportqueue.get(True,1)
            self.reports += 1
            self.log.debug("receive report for '%s'", pj.hostname)
            pj.inprocess = False
            return pj
        except Queue.Empty: pass


    def cycleLoop(self):
        self.reportqueue = Queue.Queue()
        self.pingThread = PingThread(self.reportqueue,
                                    self.tries, self.timeOut, self.chunk)
        self.sent = self.reports = 0
        pjgen = self.pingtree.pjgen()
        for i, pj in enumerate(pjgen):
            if i > self.chunk: break
            self.sendPing(pj)
        self.pingThread.start()
        while self.reports < self.sent or not self.pingThread.isAlive():
            self.log.debug("reports=%s sent=%s", self.reports, self.sent)
            try: 
                pj = pjgen.next()
                self.sendPing(pj)
            except StopIteration: pass
            pj = self.receiveReport()
            if not pj: continue
            try:
                self.log.debug("processing pj for %s" % pj.hostname)

                # ping attempt failed
                if pj.rtt == -1:
                    pj.status += 1
                    if pj.status == 1:         
                        self.log.debug("first failure '%s'", pj.hostname)
                        # if our path back is currently clear add our parent
                        # to the ping list again to see if path is really clear
                        # and then reping ourself.
                        if not pj.checkpath():
                            routerpj = pj.routerpj()
                            if routerpj: self.sendPing(routerpj)
                            self.sendPing(pj)
                    else:
                        failname = pj.checkpath()
                        if failname:
                            pj.eventState = 3 #suppressed FIXME
                            pj.message += (", failed at %s" % failname)
                        self.log.warn(pj.message)
                        self.sendEvent(pj)
                # device was down and message sent but is back up
                elif pj.status > 1:
                    pj.severity = 0
                    self.sendEvent(pj)
                    pj.status = 0
                    self.log.info(pj.message)
                # device was down no message sent but is back up
                elif pj.status == 1:
                    pj.status = 0
                #self.log.debug(pj.message)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("processing pj for '%s'", pj.hostname)
        self.pingThread.stop()


    def mainLoop(self):
        # for the first run, quit on failure
        if self.options.cycle:
            while 1:
                start = time.time()
                try:
                    self.loadConfig()
                    self.log.info("starting ping cycle %s" % (time.asctime()))
                    #self.sendHeartbeat()
                    self.cycleLoop()
                    self.log.info("end ping cycle %s" % (time.asctime()))
                    self.log.info("sent %d pings in %3.2f seconds" % 
                                (self.sent, (time.time() - start)))
                except (SystemExit, KeyboardInterrupt): raise
                except:
                    self.log.exception("unknown exception in main loop")
                runtime = time.time() - start
                if runtime < self.cycleInterval:
                    time.sleep(self.cycleInterval - runtime)
        else:
            self.loadConfig()
            self.cycleLoop()
        self.stop()
        self.log.info("stopped")


    def stop(self):
        """Stop zenping and its child threads.
        """
        self.log.info("stopping...")
        if hasattr(self,"pingThread"):
            self.pingThread.stop()
        self.eventThread.stop()


    def sendHeartbeat(self):
        """Send a heartbeat event for this monitor.
        """
        pass
#        evt = EventHeartbeat(socket.getfqdn(), "zenping")
#        self._evqueue.put(evt)


    def sendEvent(self, pj):
        """send an event to NcoProduct
        if nosev is true then don't use severity in Identifier"""
        evt = Event(
            device=pj.hostname, 
            component="icmp", 
            ipAddress=pj.ipaddr, 
            summary=pj.message, 
            severity=pj.severity,
            eventClass=PingStatus,
            eventGroup=self.eventGroup, 
            agent=self.agent, 
            manager=self.hostname)
        evstate = getattr(pj, 'eventState', None)
        if evstate is not None: evt.eventState = evstate
        self.eventThread.sendEvent(evt)



    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--configpath', dest='configpath',
                default="Monitors/StatusMonitors/localhost",
                help="path to our monitor config ie: "
                     "/Monitors/StatusMonitors/localhost")
        self.parser.add_option('--name', dest='name',
                help="name to use when looking up our record in the dmd"
                     "defaults to our fqdn as returned by socket.getfqdn")


if __name__=='__main__':
    if sys.platform == 'win32':
        time.time = time.clock
    pm = ZenPing()
    pm.mainLoop()
