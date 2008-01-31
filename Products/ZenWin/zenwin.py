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

from socket import getfqdn
from WMIC import WMIClient
import pywintypes

import Globals
from WinCollector import WinCollector
from Constants import TIMEOUT_CODE
from Products.ZenEvents.ZenEventClasses import Status_Wmi_Conn, Status_WinService
from Products.ZenEvents import Event
from Products.ZenUtils.Utils import unused

ERRtimeout = 1726

class zenwin(WinCollector):

    name = agent = "zenwin"
    attributes = WinCollector.attributes + ('winmodelerCycleInterval',)

    def __init__(self):
        WinCollector.__init__(self)
        self.wmiprobs = []
        self.devices = []
        self.watchers = {}
        self.statmsg = "Windows Service '%s' is %s"
        self.winCycleInterval = 60
        self.start()

    def mkevt(self, devname, svcname, msg, sev):
        "Compose an event"
        evt = dict(summary=msg,
                   eventClass=Status_WinService,
                   device=devname,
                   severity=sev,
                   agent=self.agent,
                   component=svcname,
                   eventGroup= "StatusTest",
                   manager=getfqdn())
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
        if status == 0:
            msg = self.statmsg % (name, "down")
            self.sendEvent(self.mkevt(device.id, name, msg, severity))
            self.log.info("svc down %s, %s", device.id, name)
            
    def serviceRunning(self, device, name):
        self.log.info('%s: %s running' % (device.id, name))
        if name not in device.services: return
        status, severity = device.services[name]
        device.services[name] = 0, severity
        if status != 0:
            msg = self.statmsg % (name, "up")
            self.sendEvent(self.mkevt(device.id, name, msg, 0))
            self.log.info("svc up %s, %s", device.id, name)


    def scanDevice(self, device):
        if not device.services:
            return None
        wql = "select Name from Win32_Service where State='Running'"
        wmic = WMIClient(device)
        wmic.connect()
        svcs = [ svc.Name for svc in wmic.query(wql) ]
        for name, (status, severity) in device.services.items():
            self.log.debug("service: %s status: %d", name, status)
            if name not in svcs:
                self.serviceStopped(device, name)
            elif status > 0:
                self.serviceRunning(device, name)
        wmic.close()

    def getWatcher(self, device):
        wql = ("""SELECT * FROM __InstanceModificationEvent within 5 where """
               """TargetInstance ISA 'Win32_Service' """)
        wmic = WMIClient(device)
        wmic.connect()
        return wmic.watcher(wql)

    def processDevice(self, device):
        w = self.watchers.get(device.id, None)
        if not w:
            self.scanDevice(device)
            self.deviceUp(device)
            self.watchers[device.id] = w = self.getWatcher(device)
        try:
            self.log.debug("Querying %s", device.id)
            s = w.nextEvent(100)
            self.deviceUp(device)
            if not s.state:
                return
            if s.state == 'Stopped':
                self.serviceStopped(device, s.name)
            if s.state == 'Running':
                self.serviceRunning(device, s.name)
        except pywintypes.com_error, e:
            code,txt,info,param = e
            if info:
                wcode, source, descr, hfile, hcont, scode = info
                if wcode == ERRtimeout:
                    return
                self.log.debug("Codes: %r %r %r %r %r %r" % info)
                scode = abs(scode)
            if scode != TIMEOUT_CODE:
                self.deviceDown(device, '%d: %s' % (code, txt))

    def processLoop(self):
        for device in self.devices:
            if device.id in self.wmiprobs:
                self.log.debug("WMI problems on %s: skipping" % device.id)
                continue
            try:
                self.processDevice(device)
            except Exception, ex:
                raise
                self.deviceDown(device, str(ex))

    def deviceDown(self, device, message):
        if device.id in self.watchers:
            del self.watchers[device.id]
        msg = self.printComErrorMessage(message)
        if not msg:
            msg = "WMI connect error on %s: %s" % (device.id, message)
        self.sendEvent(dict(summary=msg,
                            eventClass=Status_Wmi_Conn,
                            device=device.id,
                            severity=Event.Error,
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
                                eventClass=Status_Wmi_Conn,
                                device=device.id,
                                severity=Event.Clear,
                                agent=self.agent,
                                component=self.name))

    def updateConfig(self, cfg):
        WinCollector.updateConfig(self, cfg)
        self.heartbeatTimeout = self.winCycleInterval * 3

    def fetchDevices(self, driver):
        yield self.config().callRemote('getDeviceListByMonitor',
                                       self.options.monitor)
        yield self.config().callRemote('getDeviceConfigAndWinServices', 
            driver.next())
        self.updateDevices(driver.next())

    def cycleInterval(self):
        return self.winCycleInterval
        
    def buildOptions(self):
        WinCollector.buildOptions(self)


if __name__ == "__main__":
    zw = zenwin()
    zw.run()
