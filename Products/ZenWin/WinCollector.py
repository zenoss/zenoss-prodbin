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

import sys
import os
import time
from socket import getfqdn
import pythoncom

from twisted.internet import reactor, defer

import Globals
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon as Base
from Products.ZenEvents.ZenEventClasses import Heartbeat
from Products.ZenUtils.Driver import drive, driveLater

from StatusTest import StatusTest
from WinServiceTest import WinServiceTest
from WinEventlog import WinEventlog

TIMEOUT_CODE = 2147209215
RPC_ERROR_CODE = 2147023170

class WinCollector(Base):

    configCycleInterval = 20.

    initialServices = ['EventService', 'WmiConfig']
    attributes = ('configCycleInterval',)

    heartbeat = dict(eventClass=Heartbeat,
                     device=getfqdn(),
                     component='zenwin')
    deviceConfig = 'getDeviceWinInfo'

    def __init__(self):
        self.heartbeat['component'] = self.agent
        self.wmiprobs = []
        Base.__init__(self)


    def processLoop(self):
        pass


    def startScan(self, unused=None):
        drive(self.scanCycle)


    def scanCycle(self, driver):
        now = time.time()
        try:
            yield self.eventService().callRemote('getWmiConnIssues')
            self.wmiprobs = [e[0] for e in driver.next()]
            self.log.debug("Wmi Probs %r", self.wmiprobs)
            self.processLoop()
            self.sendEvent(self.heartbeat)
        except Exception, ex:
            self.log.exception("Error processing main loop")
        delay = time.time() - now
        driveLater(max(0, self.cycleInterval() - delay), self.scanCycle)

    def cycleInterval(self):
        return 60
        
    def buildOptions(self):
        Base.buildOptions(self)
        self.parser.add_option('-d', '--device', 
                               dest='device', 
                               default=None,
                               help="single device to collect")
        self.parser.add_option('--debug', 
                               dest='debug', 
                               default=False,
                               help="turn on additional debugging")


    def configService(self):
        return self.services.get('WmiConfig', FakeRemote())


    def updateDevices(self, cfg):
        pass


    def updateConfig(self, cfg):
        cfg = dict(cfg)
        for attribute in self.attributes:
            current = getattr(self, attribute, None)
            value = cfg.get(attribute)
            if current is not None and current != value:
                self.log.info("Setting %s to %r", attribute, value);
                setattr(self, attribute, value)

    def error(self, why):
        why.printTraceback()
        self.log.error(why.getErrorMessage())


    def startConfigCycle(self):
        def doReconfigure(driver):
            try:
                yield self.configService().callRemote('getConfig')
                self.updateConfig(driver.next())
                yield self.configService().callRemote(self.deviceConfig)
                self.updateDevices(driver.next())
            except Exception, ex:
                self.log.exception("Error fetching config")
            driveLater(self.configCycleInterval * 60, doReconfigure)
        return drive(doReconfigure)

    def connected(self):
        d = self.startConfigCycle()
        d.addCallback(self.startScan)
