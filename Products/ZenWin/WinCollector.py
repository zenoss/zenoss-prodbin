###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2008 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from Products.ZenHub.PBDaemon import PBDaemon, FakeRemote
from Products.ZenEvents.ZenEventClasses import App_Start, Clear
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.Utils import unused

# needed by pb
from Products.DataCollector import DeviceProxy
from Products.DataCollector.Plugins import PluginLoader
unused(DeviceProxy, PluginLoader)

from twisted.internet import reactor
from twisted.python.failure import Failure

import time

DEFAULT_QUERY_TIMEOUT = 100

class WinCollector(PBDaemon):

    configCycleInterval = 20.

    initialServices = PBDaemon.initialServices + [
        'Products.ZenWin.services.WmiConfig'
        ]

    attributes = ('configCycleInterval',)

    def __init__(self):
        self.wmiprobs = []
        self.devices = []
        self.watchers = {}
        PBDaemon.__init__(self)
        self.reconfigureTimeout = None

    def remote_notifyConfigChanged(self):
        self.log.info("Async config notification")
        if self.reconfigureTimeout and not self.reconfigureTimeout.called:
            self.reconfigureTimeout.cancel()
        self.reconfigureTimeout = reactor.callLater(30, drive, self.reconfigure)


    def stopScan(self, unused=None):
        self.stop()


    def scanCycle(self, driver):
        now = time.time()
        try:
            yield self.eventService().callRemote('getWmiConnIssues')
            self.wmiprobs = [e[0] for e in driver.next()]
            self.log.debug("Wmi Probs %r", self.wmiprobs)
            yield self.processLoop()
            driver.next()
            delay = time.time() - now
            if not self.options.cycle:
                self.stopScan()
            else:
                self.heartbeat()
                cycle = self.cycleInterval()
                driveLater(max(0, cycle - delay), self.scanCycle)
                count = len(self.devices)
                if self.options.device:
                    count = 1
                self.sendEvents(
                    self.rrdStats.gauge('cycleTime', cycle, delay) +
                    self.rrdStats.gauge('devices', cycle, count)
                    )
                self.log.info("Scanned %d devices in %.1f seconds",
                              count, delay)
        except (Failure, Exception), ex:
            self.log.exception("Error processing main loop")


    def processLoop(self):
        raise NotImplementedError("You must override this method.")


    def cycleInterval(self):
        raise NotImplementedError("You must override this method")


    def configService(self):
        return self.services.get(
            'Products.ZenWin.services.WmiConfig', FakeRemote()
            )


    def updateDevices(self, devices):
        self.devices = devices


    def remote_deleteDevice(self, deviceId):
        self.devices = [i for i in self.devices if i.id != deviceId]


    def error(self, why):
        self.log.error(why.getErrorMessage())


    def updateConfig(self, cfg):
        cfg = dict(cfg)
        for attribute in self.attributes:
            current = getattr(self, attribute, None)
            value = cfg.get(attribute)
            if current is not None and current != value:
                self.log.info("Setting %s to %r", attribute, value);
                setattr(self, attribute, value)
        self.heartbeatTimeout = self.cycleInterval() * 3


    def start(self):
        self.log.info("Starting %s", self.name)
        self.sendEvent(dict(summary='Starting %s' % self.name,
                            eventClass=App_Start,
                            device=self.options.monitor,
                            severity=Clear,
                            component=self.name))

        
    def startScan(self, unused=None):
        self.start()
        d = drive(self.scanCycle)

    
    def reconfigure(self, driver):
        try:
            yield self.eventService().callRemote('getWmiConnIssues')
            self.wmiprobs = [e[0] for e in driver.next()]
            self.log.debug("Ignoring devices %r", self.wmiprobs)
            
            yield self.configService().callRemote('getConfig')
            self.updateConfig(driver.next())

            yield drive(self.fetchDevices)
            driver.next()
            
            yield self.configService().callRemote('getThresholdClasses')
            self.remote_updateThresholdClasses(driver.next())

            yield self.configService().callRemote('getCollectorThresholds')
            self.rrdStats.config(self.options.monitor, self.name, driver.next())
        except Exception, ex:
            self.log.exception("Error fetching config")


    def startConfigCycle(self):
        def driveAgain(result):
            driveLater(self.configCycleInterval * 60, self.reconfigure)
            return result
        return drive(self.reconfigure).addBoth(driveAgain)


    def connected(self):
        d = self.startConfigCycle()
        d.addCallback(self.startScan)


    def buildOptions(self):
        PBDaemon.buildOptions(self)
        self.parser.add_option('-d', '--device', 
            dest='device', 
            default=None,
            help="single device to collect")
        self.parser.add_option('--debug', 
            dest='debug', 
            default=False,
            action='store_true',
            help="turn on additional debugging")
        self.parser.add_option('--proxywmi', 
            dest='proxywmi', 
            default=False,
            action='store_true',
            help="use a process proxy to avoid long-term blocking") 
        self.parser.add_option('--queryTimeout', 
            dest='queryTimeout', 
            default=DEFAULT_QUERY_TIMEOUT,
            help='The number of milliseconds to wait for WMI query to respond.'
                ' Default value is %s' % DEFAULT_QUERY_TIMEOUT)


