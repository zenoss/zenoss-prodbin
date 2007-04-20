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
import gc
import time
import logging
from socket import getfqdn
import pywintypes
import pythoncom
import wmiclient

import Globals
from WinCollector import WinCollector as Base
from Products.ZenEvents.ZenEventClasses import Heartbeat

TIMEOUT_CODE = 2147209215
RPC_ERROR_CODE = 2147023170

class zeneventlog(Base):

    agent = "zeneventlog"

    def __init__(self):
        Base.__init__(self)
        self.devices = {}

    def updateDevices(self, devices):
        """get the config data from server"""
        for name, user, passwd, sev, url in devices:
            try:
                if name not in self.wmiprobs: 
                    self.log.info('wmi prob on %s skipping', name)
                    continue
                if name in self.devices:
                    continue
                self.devices[name] = self.getWatcher(name,user,passwd,sev)
            except pywintypes.com_error:
                self.log.exception("wmi connect failed on %s", name)


    def getWatcher(self, name, user, passwd, minSeverity):
        """Setup WMI connection to monitored server. 
        """
        c = wmiclient.WMI(name, user, passwd)
        c.connect()
        wql = """SELECT * FROM __InstanceCreationEvent where """\
                """TargetInstance ISA 'Win32_NTLogEvent' """\
                """and TargetInstance.EventType <= %d"""\
              % minSeverity
        return c.watcher(wql)

        
    def processLoop(self):
        """Run WMI queries in two stages ExecQuery in semi-sync mode.
        then process results later (when they have already returned)
        """
        pythoncom.PumpWaitingMessages()
        baddevices = []
        for name, w in self.devices.items():
            if name in self.wmiprobs:
                continue
            self.log.debug("polling %s", name)
            try:
                while 1:
                    lrec = w.nextEvent()
                    if not lrec.Message:
                        continue
                    self.sendEvent(self.mkevt(name, lrec))
            except pywintypes.com_error, e:
                msg = "wmi connection failed: "
                code,txt,info,param = e
                wmsg = "%s: %s" % (abs(code), txt)
                if info:
                    wcode, source, descr, hfile, hcont, scode = info
                    scode = abs(scode)
                    if descr:
                        wmsg = descr.strip()
                msg += wmsg
                if scode == TIMEOUT_CODE:
                    self.log.debug("timeout %s", name)
                elif scode == RPC_ERROR_CODE:
                    self.log.warn("%s %s", name, msg)
                else:
                    self.log.warn("%s %s", name, msg)
                    self.log.warn("removing %s", name)
                    baddevices.append(name)
        for name in baddevices:
            del self.devices[name]
        self.sendEvent(self.heartbeat)
        gc.collect()
        self.log.info("Com InterfaceCount: %d", pythoncom._GetInterfaceCount())
        self.log.info("Com GatewayCount: %d", pythoncom._GetGatewayCount())
        if hasattr(sys, "gettotalrefcount"):
            self.log.info("ref: %d", sys.gettotalrefcount())


    def mkevt(self, name, lrec):
        """Put event in the queue to be sent to the ZenEventManager.
        """
        evtkey = "%s_%s" % (lrec.SourceName, lrec.EventCode)
        sev = 4 - lrec.EventType     #lower severity by one level
        if sev < 1: sev = 1
        evt = dict(device=name,
                   eventClassKey=evtkey,
                   eventGroup=lrec.LogFile,
                   component=lrec.SourceName,
                   ntevid=lrec.EventCode,
                   summary=lrec.Message.strip(),
                   agent="zeneventlog",
                   severity=sev,
                   manager=self.manager)
        self.log.debug("device:%s msg:'%s'", name, lrec.Message)
        return evt


if __name__ == "__main__":
    zw = zeneventlog()
    zw.run()
