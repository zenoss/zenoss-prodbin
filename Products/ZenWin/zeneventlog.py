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

import gc
from socket import getfqdn
import pywintypes
import pythoncom
import wmiclient

import Globals
from WinCollector import WinCollector
from Constants import TIMEOUT_CODE, RPC_ERROR_CODE
from Products.ZenEvents.ZenEventClasses import Status_Wmi_Conn
from Products.ZenEvents import Event
from Products.ZenUtils.Utils import unused

# needed for pb/jelly
from Products.ZenHub.services import WmiConfig
unused(WmiConfig)

class zeneventlog(WinCollector):

    name = agent = "zeneventlog"

    eventlogCycleInterval = 5*60
    attributes = WinCollector.attributes + ('eventlogCycleInterval',)
    events = 0

    def __init__(self):
        WinCollector.__init__(self)
        self.devices = {}
        self.manager = getfqdn()
        self.start()

    def updateDevices(self, devices):
        """get the config data from server"""
        for lastTime, name, ip, user, passwd, sev, url in devices:
            try:
                if name in self.wmiprobs: 
                    self.log.info('wmi prob on %s skipping', name)
                    continue
                if name in self.devices:
                    continue
                self.devices[name] = self.getWatcher(name, ip, user,passwd,sev)
            except Exception, ex:
                msg = self.printComErrorMessage(ex)
                if msg.find('RPC_S_CALL_FAILED') >= 0:
                    # transient error, log it but don't create an event
                    self.log.exception('Ignoring: %s' % msg)
                    continue
                if not msg:
                    msg = 'WMI connect error on %s: %s' % (name, str(ex))
                self.log.exception(msg)
                self.sendEvent(dict(summary=msg,
                                    device=name,
                                    eventClass=Status_Wmi_Conn,
                                    agent=self.agent,
                                    severity=Event.Error,
                                    manager=self.manager,
                                    component=self.name))

    def remote_deleteDevice(self, device):
        if device in self.devices:
            del self.devices[device]
    
    def getWatcher(self, name, ip, user, passwd, minSeverity):
       """Setup WMI connection to monitored server. 
       """
       c = wmiclient.WMI(*map(str, (name, ip, user, passwd) ))
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
                    self.events += 1
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
        gc.collect()
        self.log.info("Com InterfaceCount: %d", pythoncom._GetInterfaceCount())
        self.log.info("Com GatewayCount: %d", pythoncom._GetGatewayCount())
        cycle = self.cycleInterval()
        for ev in (self.rrdStats.counter('events', cycle, self.events) +
                   self.rrdStats.gauge('comInterfaceCount', cycle,
                                       pythoncom._GetInterfaceCount()) +
                   self.rrdStats.gauge('comGatewayCount', cycle,
                                       pythoncom._GetGatewayCount())):
            self.sendEvent(ev)


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

    def cycleInterval(self):
        return self.eventlogCycleInterval
        

if __name__ == "__main__":
    zw = zeneventlog()
    zw.run()
