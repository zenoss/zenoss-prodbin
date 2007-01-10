#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import socket
import os
import time
import sys

from twisted.internet import reactor
from _mysql_exceptions import OperationalError

import Globals # make zope imports work

from Products.ZenEvents.ZenEventClasses import App_Start, App_Stop
from Products.ZenEvents.Event import Event, EventHeartbeat
from Products.ZenUtils.ZCmdBase import ZCmdBase
import ZenTcpClient 

class ZenStatus(ZCmdBase):

    agent = "ZenTCP"
    eventGroup = "TCPTest"
    stopping = False

    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        self.clients = {}
        self.count = 0
        self.hostname = socket.getfqdn()
        self.configpath = self.options.configpath
        if self.configpath.startswith("/"):
            self.configpath = self.configpath[1:]
        self.smc = self.dmd.unrestrictedTraverse(self.configpath)
        self.zem = self.dmd.ZenEventManager
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=App_Start, 
                        summary="zenstatus started",
                        severity=0, component="zenstatus"))
        self.log.info("started")


    def cycleLoop(self):
        """Our own reactor loop so we can control timeout.
        """
        start = time.time()
        self.log.debug("starting cycle loop")
        self.startTests()
        reactor.startRunning(installSignalHandlers=False)
        while self.clients and not self.stopping:
            try:
                reactor.runUntilCurrent()
                reactor.doIteration(reactor.timeout())
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected error in reactorLoop")
        self.log.debug("ended cycle loop runtime=%s", time.time()-start)

    
    def startTests(self):
        self.svcgen = self.smc.getSubComponents("IpService")
        count = 0
        while self.nextService() and self.count < self.options.parallel: pass


    def nextService(self):
        while True:
            try:
                svc = self.svcgen.next()
            except StopIteration: return False
            dev = svc.device()
            if dev.getPingStatus() > 0: 
                self.log.debug("skipping service %s on %s bad ping status.",
                                svc.name(), dev.getId())
                continue
            if not dev.monitorDevice():
                self.log.debug("skipping service %s on %s prod state too low.",
                                svc.name(), dev.getId())
                continue
            if svc.getProtocol() != "tcp":
                self.log.debug("skipping service %s on %s it is not TCP.",
                                svc.name(), dev.getId())
                continue
            self.log.debug("adding service:%s on:%s", svc.name(), dev.getId())
            self.count += 1
            timeout = getattr(dev, 'zStatusConnectTimeout', 15.0)
            d = ZenTcpClient.test(svc, timeout=timeout)
            d.addCallback(self.processTest)
            d.addErrback(self.processError)
            key = (svc.getManageIp(), svc.name())
            self.clients[key] = 1
            return True 


    def processTest(self, result):
        key, evt = result
        if evt: self.sendEvent(evt)
        self.nextService()
        if self.clients.has_key(key):
            del self.clients[key] 

        
    def processError(self, error):
        self.log.warn(error.getErrorMessage())

        
    def mainLoop(self):
        # for the first run, quit on failure
	try:
          if self.options.cycle:
            while not self.stopping:
                start = time.time()
                self.count = 0
                try:
                    self.syncdb()
                    self.log.debug("starting zenstatus cycle")
                    self.cycleLoop()
                    self.log.info("tested %d in %3.2f seconds" % 
                                (self.count, (time.time() - start)))
                    self.sendHeartbeat()
                except (SystemExit, KeyboardInterrupt): raise
                except:
                    self.log.exception("unknown exception in main loop")
                runtime = time.time() - start
                if runtime < self.options.cycletime:
                    time.sleep(self.options.cycletime - runtime)
          else:
            self.cycleLoop()
            self.sendHeartbeat()
        finally:
          self._stop()
          self.log.info("stopped")


    def stop(self):
        """Stop zenstatus and its child threads.
        """
	self.stopping = True

    def _stop(self):
        self.log.info("stopping...")
        if hasattr(self,"pingThread"):
            self.pingThread.stop()
        self.log.info("stopped")


    def sendEvent(self, evt):
        """Send an event for this monitor.
        """
        try:
            self.zem.sendEvent(evt)
        except OperationalError, e:
            self.log.warn("failed sending event: %s", e)


    def sendHeartbeat(self):
        """Send a heartbeat event for this monitor.
        """
        timeout = self.options.cycletime*3
        evt = EventHeartbeat(socket.getfqdn(), "zenstatus", timeout)
        self.sendEvent(evt)


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--configpath', dest='configpath',
                default="/Devices/Server",
                help="path to our monitor config ie: "
                     "/Devices/Server")
        self.parser.add_option('--parallel', dest='parallel', 
                default=50, type='int',
                help="number of devices to collect at one time")
        self.parser.add_option('--cycletime',
            dest='cycletime', default=60, type="int",
            help="check events every cycletime seconds")



if __name__=='__main__':
    if sys.platform == 'win32':
        time.time = time.clock
    pm = ZenStatus()
    pm.mainLoop()
