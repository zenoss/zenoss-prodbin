#!/usr/bin/env python2.1

#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__=''' PingMonitor

creates a queue of hosts to be pinged (jobs),
and pings them until they respond, or the
maximum number of pings has been sent. After
sending out all these pings, we loop in a
receive function processing everything we get
back

$Id: PingMonitor.py,v 1.70 2004/04/22 20:54:23 edahl Exp $'''

__version__ = "$Revision: 1.70 $"[11:-2]

import socket
import ip
import icmp
import os
import time
import select
import sys
import xmlrpclib
import logging
import Queue

import Globals # make zope imports work

from Products.ZenEvents.MySqlSendEvent import MySqlSendEventThread
from Products.ZenEvents.ZenEventClasses import PingStatus
from Products.ZenUtils.Utils import parseconfig, basicAuthUrl
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Ping import PingThread
import pingtree
#from StatusMonitor import StatusMonitor


#class PingMonitor(ZCmdBase, StatusMonitor):
class PingMonitor(ZCmdBase):

    agent = "PingMonitor"
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
        #StatusMonitor.__init__(self)
        self.hostname = socket.getfqdn()
        self.configpath = self.options.configpath
        if self.configpath.startswith("/"):
            self.configpath = self.configpath[1:]
        self.configCycleInterval = 0
        self.configTime = 0
        self.sendqueue = Queue.Queue()
        self.reportqueue = Queue.Queue()

        self.senderThread = MySqlSendEventThread(self.dmd.ZenEventManager)
        self._evqueue = self.senderThread.getqueue()
        self.senderThread.start()
        self.log.info("started")


    def loadConfig(self):
        "get the config data from file or server"
        if time.time()-self.configTime > self.configCycleInterval:
            self.opendb()
            self.syncdb()
            smc = self.dmd.unrestrictedTraverse(self.configpath)
            for att in self.copyattrs:
                value = getattr(smc, att)
                setattr(self, att, value)
            self.configCycleInterval = self.configCycleInterval*60
            me = self.dmd.Devices.findDevice(self.hostname)
            if me: 
                self.pingtree = pingtree.buildTree(me)
            else:
                self.log.critical("PingMonitor '%s' not found,"
                                  "ignoring network topology.",self.hostname)
                self.pingtree = Rnode(self.hostname)
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
        self.sendqueue.put(pj)


    def receiveReport(self):
        self.reports += 1
        pj = self.reportqueue.get(True)
        self.log.debug("receive for '%s'", pj.hostname)
        pj.inprocess = False
        return pj


    def cycleLoop(self):
        self.pingThread = PingThread(self.sendqueue, self.reportqueue,
                                    self.tries, self.timeOut, self.chunk)
        self.pingThread.start()
        self.sent = self.reports = 0

        pjgen = self.pingtree.pjgen()
        for i, pj in enumerate(pjgen):
            if i > self.chunk: break
            self.sendPing(pj)

        while self.reports < self.sent:
            try: 
                pj = pjgen.next()
                self.sendPing(pj)
            except StopIteration: pass
            pj = self.receiveReport()
            try:
                self.log.debug("processing pj for %s" % pj.hostname)

                # ping attempt failed
                if pj.rtt == -1:
                    pj.status += 1
                    if pj.state == 1:         
                        self.log.info("first failure '%s' skipping event")
                        return
                    pj.message = "device %s ip %s unreachable" % (
                                  pj.hostname, pj.ipaddr)
                    failname = pj.parent.checkpath()
                    if failname:
                        pj.eventState = evstates.SUPPRESSED
                        pj.message += (", failed at %s" % failname)
                    else:
                        # if our path back is currently clear add our parent
                        # to the ping list again to see if path is really clear
                        parent = self.pj.parent
                        if parent: self.sendPing(parent.pj)
                    self.sendEvent(pj)
                # device was down but is back up
                elif pj.status > 0:
                    pj.severity = 0
                    self.sendEvent(pj)
                    pj.status = 0
                    self.log.info(pj.message)
                self.log.debug(pj.message)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("processing pj for '%s'", pj.hostname)
        self.pingThread.morepkts = False


    def mainLoop(self):
        # for the first run, quit on failure
        if self.options.cycle:
            while 1:
                try:
                    self.loadConfig()
                    #self.setPingHeartbeat()
                    runtime = self.cycleLoop()
                    if runtime < self.cycleInterval:
                        time.sleep(self.cycleInterval - runtime)
                except SystemExit: raise
                except:
                    self.log.exception("unknown exception in main loop")
        else:
            self.loadConfig()
            self.cycleLoop()


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
        self._evqueue.put(evt)



    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--configpath', dest='configpath',
                default="Monitors/StatusMonitors/localhost",
                help="path to our monitor config ie: "
                     "/Monitors/StatusMonitors/localhost")


if __name__=='__main__':
    if sys.platform == 'win32':
        time.time = time.clock
    pm = PingMonitor()
    pm.mainLoop()
