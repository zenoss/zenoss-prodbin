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
from Products.ZenEvents.ZenEventClasses import Heartbeat, Status_Wmi_Conn, Status_WinSrv

from WinServiceTest import WinServiceTest
from WinEventlog import WinEventlog

class StatusTest:
    def __init__(self, name, username, password, services):
        self.name = name
        self.username = username
        self.password = password
        self.services = dict([(k.lower(), v) for k, v in services.items()])

class zenwin(Base):

    name = agent = "zenwin"
    deviceConfig  = 'getWinServices'

    def __init__(self):
        Base.__init__(self)
        self.wmiprobs = []
        self.devices = []
        self.watchers = {}
        self.statmsg = "Windows Service '%s' is %s"

    def mkevt(self, devname, svcname, msg, sev):
        "Compose an event"
        name = "WinServiceTest"
        evt = dict(device=devname, component=svcname,
                   summary=msg, eventClass=Status_WinSrv,
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
        svcs = [ svc.Name.lower() for svc in w.query(wql) ]
        nextFd = os.open('/dev/null', os.O_RDONLY)
        for name, (status, severity) in srec.services.items():
            name = name.lower()
            self.log.debug("service: %s status: %d", name, status)
            if name not in svcs:
                self.serviceStopped(srec, name)
            elif status > 0:
                self.serviceRunning(srec, name)
        w.close()
        del w
        import gc
        gc.collect()

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
            self.watchers[srec.name] = w = self.getWatcher(srec)
        try:
            s = w.nextEvent(100)
            if not s.state:
                return
            if s.state == 'Stopped':
                self.serviceStopped(srec, s.name.lower())
            if s.state == 'Running':
                self.serviceRunning(srec, s.name.lower())
        except pywintypes.com_error, e:
            code,txt,info,param = e
            if info:
                wcode, source, descr, hfile, hcont, scode = info
                scode = abs(scode)
            if scode != TIMEOUT_CODE:
                w.close()
                del self.watchers[srec.name]

    def processLoop(self):
        for device in self.devices:
            if device.name in self.wmiprobs:
                self.log.debug("WMI problems on %s: skipping" % device.name)
                continue
            try:
                self.processDevice(device)
            except Exception, ex:
	        self.sendEvent(dict(summary="Wmi error talking to %s: %s" % 
				    (device.name, ex), 
				    device=device.name,
				    agent=self.agent,
			            eventClass=Status_Wmi_Conn))
                self.wmiprobs.append(device.name)


    def updateDevices(self, devices):
        config = []
        for n,u,p,s in devices:
            if self.options.device and self.options.device != n:
                continue
            st = StatusTest(n, u, p, s)
            config.append(st) 
        if devices:
            self.devices = config
    
    def buildOptions(self):
        Base.buildOptions(self)


if __name__ == "__main__":
    zw = zenwin()
    zw.run()
