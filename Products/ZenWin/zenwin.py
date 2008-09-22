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
from Products.ZenWin.WMIClient import WMIClient
from Products.ZenWin.WinCollector import WinCollector
from Products.ZenWin.Watcher import Watcher
from Products.ZenEvents.ZenEventClasses import Status_Wmi, Status_WinService
from Products.ZenEvents.Event import Error, Clear
from Products.ZenUtils.Driver import drive

from sets import Set

from twisted.internet import defer

class zenwin(WinCollector):

    name = agent = "zenwin"
    attributes = WinCollector.attributes + ('winCycleInterval',)

    def __init__(self):
        WinCollector.__init__(self)
        self.statmsg = "Windows Service '%s' is %s"
        self.winCycleInterval = 60

    def makeEvent(self, devname, svcname, msg, sev):
        "Compose an event"
        evt = dict(summary=msg,
                   eventClass=Status_WinService,
                   device=devname,
                   severity=sev,
                   agent=self.agent,
                   component=svcname,
                   eventGroup= "StatusTest")
        if sev > 0:
            self.log.critical(msg)
        else:
            self.log.info(msg)
        return evt

    def serviceStopped(self, device, name):
        self.log.warning('%s: %s stopped' % (device.id, name))
        if name not in device.services: return
        status, severity = device.services[name]
        device.services[name] = status + 1, severity
        msg = self.statmsg % (name, "down")
        self.sendEvent(self.makeEvent(device.id, name, msg, severity))
        self.log.info("svc down %s, %s", device.id, name)
            
    def reportServices(self, device):
        for name, (status, severity) in device.services.items():
            if status > 0:
                msg = self.statmsg % (name, "down")
                self.sendEvent(self.makeEvent(device.id, name, msg, severity))
            
    def serviceRunning(self, device, name):
        if name not in device.services: return
        status, severity = device.services[name]
        device.services[name] = 0, severity
        if status != 0:
            self.log.info('%s: %s running' % (device.id, name))
            msg = self.statmsg % (name, "up")
            self.sendEvent(self.makeEvent(device.id, name, msg, 0))
            self.log.info("svc up %s, %s", device.id, name)


    def scanDevice(self, device):
        "Fetch the current state of the services on a device"
        def inner(driver):
            try:
                if not device.services:
                    driver.finish(None)
                self.log.info("Scanning %s", device.id)
                wql = "select Name from Win32_Service where State='Running'"
                wmic = WMIClient(device)
                yield wmic.connect()
                driver.next()
                yield wmic.query(dict(query=wql))
                q = driver.next()
                running = Set([ svc.name for svc in q['query'] ])
                monitored = Set(device.services.keys())
                self.log.debug("services: %s", monitored)
                for name in monitored - running:
                    self.serviceStopped(device, name)
                for name in monitored & running:
                    self.serviceRunning(device, name)
                wmic.close()
                self.log.info("Finished scanning %s", device.id)
            except Exception, ex:
                self.log.exception(ex)
                raise
        return drive(inner)


    def processDevice(self, device):
        """Run WMI queries in two stages. First get the current state,
        then incremental updates thereafter.
        """
        wql = ("""SELECT * FROM __InstanceModificationEvent within 5 where """
               """TargetInstance ISA 'Win32_Service' """)
        def inner(driver):
            try:
                self.niceDoggie(self.cycleInterval())
                w = self.watchers.get(device.id, None)
                if not w:
                    yield self.scanDevice(device)
                    driver.next()
                    self.deviceUp(device)
                    w = Watcher(device, wql)
                    yield w.connect()
                    driver.next()
                    self.watchers[device.id] = w
                else:
                    self.reportServices(device)
                    self.log.debug("Querying %s", device.id)
                    yield w.getEvents(int(self.options.queryTimeout))
                    for s in driver.next():
                        s = s.targetinstance
                        self.deviceUp(device)
                        if s.state:
                            if s.state == 'Stopped':
                                self.serviceStopped(device, s.name)
                            if s.state == 'Running':
                                self.serviceRunning(device, s.name)
            except Exception, ex:
                self.log.exception(ex)
                self.deviceDown(device, "Error reading services", ex)
                raise
            self.niceDoggie(self.cycleInterval())
        if not device.plugins:
            return defer.succeed(None)
        return drive(inner)
        
    
    def processLoop(self):
        deferreds = []
        for device in self.devices:
            if device.id in self.wmiprobs:
                self.log.debug("WMI problems on %s: skipping" % device.id)
                continue
            if not self.options.device or device.id == self.options.device:
                deferreds.append(self.processDevice(device))
        return defer.DeferredList(deferreds)


    def deviceDown(self, device, message, exception):
        if device.id in self.watchers:
            w = self.watchers.pop(device.id)
            w.close()
        self.sendEvent(dict(summary=message,
                            eventClass=Status_Wmi,
                            exception=str(exception),
                            device=device.id,
                            severity=Error,
                            agent=self.agent,
                            component=self.name))
        self.wmiprobs.append(device.id)
        self.log.warning("WMI Connection to %s went down" % device.id)


    def deviceUp(self, device):
        if device.id in self.wmiprobs:
            self.wmiprobs.remove(device.id)
            self.log.info("WMI Connection to %s up" % device.id)
            msg = "WMI connection to %s up." % device.id
            self.sendEvent(dict(summary=msg,
                                eventClass=Status_Wmi,
                                device=device.id,
                                severity=Clear,
                                agent=self.agent,
                                component=self.name))


    def updateConfig(self, cfg):
        WinCollector.updateConfig(self, cfg)
        self.heartbeatTimeout = self.winCycleInterval * 3


    def fetchDevices(self, driver):
        yield self.configService().callRemote('getDeviceListByMonitor',
                                              self.options.monitor)
        yield self.configService().callRemote('getDeviceConfigAndWinServices', 
                                              driver.next())
        self.updateDevices(driver.next())


    def cycleInterval(self):
        return self.winCycleInterval


if __name__ == "__main__":
    zw = zenwin()
    zw.run()
