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
from Products.ZenWin.Watcher import Watcher
from Products.ZenWin.WinCollector import WinCollector
from Products.ZenUtils.Driver import drive
from Products.ZenEvents.ZenEventClasses import Status_Wmi
from Products.ZenEvents import Event

from twisted.internet import defer

class zeneventlog(WinCollector):

    name = agent = "zeneventlog"

    eventlogCycleInterval = 5*60
    attributes = WinCollector.attributes + ('eventlogCycleInterval',)
    events = 0


    def fetchDevices(self, driver):
        yield self.configService().callRemote(
            'getDeviceListByMonitor', self.options.monitor)
        yield self.configService().callRemote(
            'getDeviceConfigAndWinServices', driver.next())
        self.updateDevices(driver.next())


    def processDevice(self, device):
        """Scan a single device."""
        self.log.debug("polling %s", device.id)
        wql = """SELECT * FROM __InstanceCreationEvent where """\
              """TargetInstance ISA 'Win32_NTLogEvent' """\
              """and TargetInstance.EventType <= %d"""\
              % device.zWinEventlogMinSeverity
        def inner(driver):
            try:
                self.niceDoggie(self.cycleInterval())
                w = self.watchers.get(device.id, None)
                if not w:
                    self.log.debug("Creating watcher of %s", device.id)
                    w = Watcher(device, wql)
                    self.log.info("Connecting to %s", device.id)
                    yield w.connect()
                    driver.next()
                    self.log.info("Connected to %s", device.id)
                    self.watchers[device.id] = w
                while 1:
                    yield w.getEvents(int(self.options.queryTimeout))
                    events = driver.next()
                    self.log.debug("Got %d events", len(events))
                    if not events: break
                    for lrec in events:
                        self.events += 1
                        self.sendEvent(self.makeEvent(device.id, lrec))
            except Exception, ex:
                self.log.exception("Exception getting windows events: %s", ex)
                self.sendEvent(dict(summary="Error reading events",
                                    component=self.agent,
                                    exception=str(ex),
                                    eventClass=Status_Wmi,
                                    device=device.id,
                                    severity=Event.Error,
                                    agent=self.agent))
                self.log.warning("Closing watcher of %s", device.id)
                if self.watchers.has_key(device.id):
                    w = self.watchers.pop(device.id)
                    w.close()
        return drive(inner)


    def processLoop(self):
        "Fetch event updates from all the devices"
        devices = []
        for device in self.devices:
            if not device.plugins:
                continue
            if self.options.device and device.id != self.options.device:
                continue
            if device.id in self.wmiprobs:
                self.log.debug("WMI problems on %s: skipping" % device.id)
                continue
            devices.append(device)
        def inner(driver):
            try:
                cycle = self.cycleInterval()
                deferreds = []
                yield defer.DeferredList(map(self.processDevice, devices))
                driver.next()
                for ev in (
                    self.rrdStats.counter('events', cycle, self.events) +
                    self.rrdStats.gauge('devices', cycle, len(deferreds))
                    ):
                    self.sendEvent(ev)
            except Exception, ex:
                self.log.exception(ex)
        return drive(inner)


    def makeEvent(self, name, lrec):
        """Put event in the queue to be sent to the ZenEventManager.
        """
        lrec = lrec.targetinstance
        evtkey = "%s_%s" % (lrec.sourcename, lrec.eventcode)
        sev = 4 - lrec.eventtype     #lower severity by one level
        if sev < 1: sev = 1
        evt = dict(device=name,
                   eventClassKey=evtkey,
                   eventGroup=lrec.logfile,
                   component=lrec.sourcename,
                   ntevid=lrec.eventcode,
                   summary=lrec.message.strip(),
                   agent="zeneventlog",
                   severity=sev,
                   monitor=self.options.monitor)
        self.log.debug("device:%s msg:'%s'", name, lrec.message)
        return evt


    def cycleInterval(self):
        return self.eventlogCycleInterval
        

if __name__ == "__main__":
    zw = zeneventlog()
    zw.run()
