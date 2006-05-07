#!/usr/bin/env python2.1

#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
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
import sys
import Queue

import Globals # make zope imports work

from Products.ZenEvents.ZenEventClasses import AppStart, AppStop, DNSFail
from Products.ZenEvents.ZenEventClasses import PingStatus
from Products.ZenEvents.Event import Event, EventHeartbeat
from Products.ZenUtils.Utils import parseconfig, basicAuthUrl
from Products.ZenUtils.ZCmdBase import ZCmdBase
from AsyncPing import Ping
import pingtree

from twisted.internet import reactor, defer

def findIp():
    try:
        return socket.gethostbyname(socket.getfqdn())
    except socket.gaierror:
        # find the first non-loopback interface address
        import re
        ifconfigs = ['/sbin/ifconfig',
                     '/usr/sbin/ifconfig',
                     '/usr/bin/ifconfig',
                     '/bin/ifconfig']
        ifconfig = filter(os.path.exists, ifconfigs)[0]
        fp = os.popen(ifconfig + ' -a')
        config = fp.read().split('\n\n')
        fp.close()
        pat = r'(addr:|inet) *([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})[^0-9]'
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


class ZenPing(ZCmdBase):

    agent = "ZenPing"
    eventGroup = "Ping"

    pathcheckthresh = 10

    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        self.hostname = socket.getfqdn()
        self.configpath = self.options.configpath
        if self.configpath.startswith("/"):
            self.configpath = self.configpath[1:]
        self.configCycleInterval = 0
        self.configTime = 0
        self.reportqueue = Queue.Queue()

        self.zem = self.dmd.ZenEventManager
        self.zem.sendEvent(Event(device=socket.getfqdn(), 
                                 eventClass=AppStart, 
                                 summary="zenping started",
                                 severity=0,
                                 component="zenping"))
        self.log.info("started")

    def loadConfig(self):
        "get the config data from file or server"
        if time.time()-self.configTime > self.configCycleInterval:
            smc = self.dmd.unrestrictedTraverse(self.configpath)
            for att in ("timeOut", "tries", "chunk",
                        "cycleInterval", "configCycleInterval",
                        "maxFailures",):
                setattr(self, att, getattr(smc, att))
            self.configCycleInterval *= 60
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
                self.pingtree = pingtree.Rnode(findIp(), self.hostname, 0)
            devices = smc.getPingDevices()
            self.prepDevices(devices)
            self.configTime = time.time()


    def prepDevices(self, devices):
        """resolve dns names and make StatusTest objects"""
        for device in devices:
            status = device.getStatus(PingStatus, state=2)
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
        pj.deferred.addCallback(self.receiveReport)
        self.pinger.sendPacket(pj)


    def receiveReport(self, pj):
        self.log.debug('receiveReport %s', pj)
        self.reports += 1
        self.log.debug("receive report for '%s'", pj.hostname)
        pj.inprocess = False
        try:
            pj = self.pjgen.next()
            self.sendPing(pj)
        except StopIteration:
            pass
        except Exception, ex:
            import traceback
            traceback.print_exc(ex)

        if self.reports == self.sent:
            self.sendHeartbeat()
            runtime = time.time() - self.start
            self.log.info("sent %d pings in %3.2f seconds" %
                          (self.sent, runtime))
            if self.options.cycle:
                nextRun = max(self.cycleInterval - runtime, 0)
                reactor.callLater(nextRun, self.startSynchDb)
            else:
                self.stop()
            
        if pj.rtt == -1:
                pj.status += 1
                if pj.status == 1:         
                    self.log.debug("first failure '%s'", pj.hostname)
                    # if our path back is currently clear add our parent
                    # to the ping list again to see if path is really clear
                    # and then re-ping ourself.
                    if not pj.checkpath():
                        routerpj = pj.routerpj()
                        if routerpj:
                            self.sendPing(routerpj)
                        self.sendPing(pj)
                else:
                    failname = pj.checkpath()
                    if failname:
                        pj.eventState = 2 # suppressed FIXME
                        pj.message += (", failed at %s" % failname)
                    self.log.warn(pj.message)
                    self.sendEvent(pj)
        # device was down and message sent but is back up
        elif pj.status > 0:
            pj.severity = 0
            self.sendEvent(pj)
            pj.status = 0
            self.log.info(pj.message)

    def startCycleLoop(self):
        self.pinger = Ping(self.tries, self.timeOut, self.chunk)
        self.sent = self.reports = 0
        self.pjgen = self.pingtree.pjgen()
        for i, pj in enumerate(self.pjgen):
            if i > self.chunk: break
            self.sendPing(pj)

    def startSynchDb(self):
        self.start = time.time()
        self.syncdb()
        self.startLoadConfig()

    def startLoadConfig(self):
        self.loadConfig()
        self.startCycleLoop()

    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()

    def start(self):
        self.startSynchDb()

    def stop(self):
        self.log.info("stopping...")
        self.zem.sendEvent(Event(device=socket.getfqdn(), 
                                 eventClass=AppStop, 
                                 summary="zenping stopped",
                                 severity=4, component="zenping"))
        reactor.stop()


    def sendHeartbeat(self):
        'Send a heartbeat event for this monitor.'
        timeout = self.cycleInterval*3
        evt = EventHeartbeat(socket.getfqdn(), "zenping", timeout)
        self.zem.sendEvent(evt)


    def sendEvent(self, pj):
        """Send an event to event backend.
        """
        evt = Event(device=pj.hostname, 
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
        self.zem.sendEvent(evt)

    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--configpath',
                               dest='configpath',
                               default="Monitors/StatusMonitors/localhost",
                               help="path to our monitor config ie: "
                               "/Monitors/StatusMonitors/localhost")
        self.parser.add_option('--name',
                               dest='name',
                               help=("name to use when looking up our "
                                     "record in the dmd "
                                     "defaults to our fqdn as returned "
                                     "by socket.getfqdn"))



if __name__=='__main__':
    if sys.platform == 'win32':
        time.time = time.clock
    pm = ZenPing()
    pm.start()
    reactor.run(installSignalHandlers=False)
    pm.log.info("stopped")
