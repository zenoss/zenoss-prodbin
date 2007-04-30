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
from wmiclient import WMI
import pywintypes

from twisted.internet import reactor, defer

import Globals
from WinCollector import WinCollector as Base, TIMEOUT_CODE
from Products.ZenHub.services import WmiConfig
from Products.ZenEvents.ZenEventClasses import Heartbeat, Status_Wmi_Conn, Status_WinService
from Products.ZenEvents import Event

from WinServiceTest import WinServiceTest
from WinEventlog import WinEventlog

ERRtimeout = 88

class StatusTest:
    def __init__(self, name, username, password, services):
        self.name = name
        self.username = username
        self.password = password
        self.services = dict([(k, v) for k, v in services.items()])

class zenwin(Base):

    name = agent = "zenwin"
    deviceConfig  = 'getWinServices'
    attributes = Base.attributes + ('winmodelerCycleInterval',)

    def __init__(self):
        Base.__init__(self)
        self.wmiprobs = []
        self.devices = []
        self.watchers = {}
        self.statmsg = "Windows Service '%s' is %s"
        self.winCycleInterval = 60
        self.start()

    def mkevt(self, devname, svcname, msg, sev):
        "Compose an event"
        name = "WinServiceTest"
        evt = dict(device=devname, component=svcname,
                   summary=msg, eventClass=Status_WinService,
                   agent= self.agent, severity= sev,
                   eventGroup= "StatusTest", manager=getfqdn())
        if sev > 0:
            self.log.critical(msg)
        else:
            self.log.info(msg)
        return evt

    def serviceStopped(self, srec, name):
        self.log.warning('%s: %s stopped' % (srec.name, name))
        if name not in srec.services: return
        status, severity = srec.services[name]
        srec.services[name] = status + 1, severity
        if status == 0:
            msg = self.statmsg % (name, "down")
            self.sendEvent(self.mkevt(srec.name, name, msg, severity))
            self.log.info("svc down %s, %s", srec.name, name)
            
    def serviceRunning(self, srec, name):
        self.log.info('%s: %s running' % (srec.name, name))
        if name not in srec.services: return
        status, severity = srec.services[name]
        srec.services[name] = 0, severity
        if status != 0:
            msg = self.statmsg % (name, "up")
            self.sendEvent(self.mkevt(srec.name, name, msg, 0))
            self.log.info("svc up %s, %s", srec.name, name)

    def scanDevice(self, srec):
        if not srec.services:
            return None
        wql = "select Name from Win32_Service where State='Running'"
        w = WMI(srec.name, srec.username, srec.password)
        w.connect()
        svcs = [ svc.Name for svc in w.query(wql) ]
        nextFd = os.open('/dev/null', os.O_RDONLY)
        for name, (status, severity) in srec.services.items():
            self.log.debug("service: %s status: %d", name, status)
            if name not in svcs:
                self.serviceStopped(srec, name)
            elif status > 0:
                self.serviceRunning(srec, name)
        w.close()

    def getWatcher(self, srec):
        wql = ("""SELECT * FROM __InstanceModificationEvent within 5 where """
               """TargetInstance ISA 'Win32_Service' """)
        w = WMI(srec.name, srec.username, srec.password)
        w.connect()
        return w.watcher(wql)

    def processDevice(self, srec):
        w = self.watchers.get(srec.name, None)
        if not w:
            self.scanDevice(srec)
            self.deviceUp(srec)
            self.watchers[srec.name] = w = self.getWatcher(srec)
        try:
            self.log.debug("Querying %s", srec.name)
            s = w.nextEvent(100)
            self.deviceUp(srec)
            if not s.state:
                return
            if s.state == 'Stopped':
                self.serviceStopped(srec, s.name)
            if s.state == 'Running':
                self.serviceRunning(srec, s.name)
        except pywintypes.com_error, e:
            code,txt,info,param = e
            if info:
                wcode, source, descr, hfile, hcont, scode = info
                if wcode == ERRtimeout:
                    return
                self.log.debug("Codes: %r %r %r %r %r %r" % info)
                scode = abs(scode)
            if scode != TIMEOUT_CODE:
                self.deviceDown(srec, str(e))

    def processLoop(self):
        print [d.name for d in self.devices]
        for device in self.devices:
            if device.name in self.wmiprobs:
                self.log.debug("WMI problems on %s: skipping" % device.name)
                continue
            try:
                self.processDevice(device)
            except Exception, ex:
                self.deviceDown(device, str(ex))

    def deviceDown(self, device, message):
        if device.name in self.watchers:
            del self.watchers[device.name]
        self.sendEvent(dict(summary="Wmi error talking to %s: %s" % 
                            (device.name, message),
                            severity=Event.Error,
                            device=device.name,
                            agent=self.agent,
                            eventClass=Status_Wmi_Conn))
        self.wmiprobs.append(device.name)
        self.log.warning("WMI Connection to %s went down" % device.name)

    def deviceUp(self, device):
        print device.name, self.wmiprobs
        print device.name in self.wmiprobs
        if device.name in self.wmiprobs:
            self.wmiprobs.remove(device.name)
            self.log.info("WMI Connection to %s up" % device.name)
            self.sendEvent(dict(summary="Wmi connection to %s up." % device.name,
                                severity=Event.Clear,
                                device=device.name,
                                agent=self.agent,
                                eventClass=Status_Wmi_Conn))

    def updateConfig(self, cfg):
        Base.updateConfig(self, cfg)
        self.heartbeat['timeout'] = self.winCycleInterval*3

    def updateDevices(self, devices):
        config = []
        for n,u,p,s in devices:
            if self.options.device and self.options.device != n:
                continue
            st = StatusTest(n, u, p, s)
            config.append(st) 
        if devices:
            self.devices = config

    def remote_deleteDevice(self, device):
        self.devices = [d for d in self.devices if d.name != device]
    
    def cycleInterval(self):
        return self.winCycleInterval
        
    def buildOptions(self):
        Base.buildOptions(self)


if __name__ == "__main__":
    zw = zenwin()
    zw.run()
