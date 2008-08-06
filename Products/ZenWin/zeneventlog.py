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


import Globals
from Products.ZenEvents.ZenEventClasses import Status_Wmi
from Products.ZenEvents import Event

from Products.ZenWin.WinCollector import WinCollector
from Products.ZenWin.Constants import TIMEOUT_CODE, RPC_ERROR_CODE


class zeneventlog(WinCollector):

    name = agent = "zeneventlog"

    eventlogCycleInterval = 5*60
    attributes = WinCollector.attributes + ('eventlogCycleInterval',)
    events = 0

    def __init__(self):
        WinCollector.__init__(self)
        self.manager = getfqdn()


    def fetchDevices(self, driver):
        yield self.configService().callRemote('getDeviceListByMonitor',
                                       self.options.monitor)
        yield self.configService().callRemote('getDeviceConfigAndWinServices', 
            driver.next())
        self.updateDevices(driver.next())

    def processDevice(self, device):
        self.log.debug("polling %s", device.id)
        try:
            wql = """SELECT * FROM __InstanceCreationEvent where """\
                  """TargetInstance ISA 'Win32_NTLogEvent' """\
                  """and TargetInstance.EventType <= %d"""\
                  % device.zWinEventlogMinSeverity
            if not self.watchers.has_key(device.id):
                self.log.warning("Creating watcher of %s", device.id)
                self.watchers[device.id] = self.getWatcher(device, wql)
            w = self.watchers[device.id]

            while 1:
                lrec = w.nextEvent()
                if not lrec.message:
                    continue
                self.events += 1
                self.sendEvent(self.mkevt(device.id, lrec))
            return
        except pywintypes.com_error, e:
            code,txt,info,param = e
            wmsg = "%s: %s" % (abs(code), txt)
            if info:
                wcode, source, descr, hfile, hcont, scode = info
                scode = abs(scode)
                if descr:
                    wmsg = descr.strip()
                if scode == TIMEOUT_CODE:
                    self.log.debug("timeout (no events) %s", device.id)
                    return
            self.log.warn("%s %s", device.id, "wmi connection failed: ", wmsg)
        except Exception, ex:
            self.log.exception("Exception getting windows events: %s", ex)
            self.sendEvent(dict(summary="Error reading wmi events",
                                exception=str(ex),
                                eventClass=Status_Wmi,
                                device=device.id,
                                severity=Event.Error,
                                agent=self.agent))
        self.log.warning("Closing watcher of %s", device.id)
        if self.watchers.has_key(device.id):
            w = self.watchers.pop(device.id)
            w.close()

        
        
    def processLoop(self):
        """Run WMI queries in two stages ExecQuery in semi-sync mode.
        then process results later (when they have already returned)
        """
        cycle = self.cycleInterval()
        pythoncom.PumpWaitingMessages()
        for device in self.devices:
            if not device.plugins: continue
            if device.id in self.wmiprobs:
                self.log.debug("WMI problems on %s: skipping" % device.id)
                continue
            try:
                self.processDevice(device)
            finally:
                self.niceDoggie(cycle)

        self.log.debug("Com InterfaceCount: %d", pythoncom._GetInterfaceCount())
        self.log.debug("Com GatewayCount: %d", pythoncom._GetGatewayCount())
        for ev in (self.rrdStats.counter('events', cycle, self.events) +
                   self.rrdStats.gauge('comInterfaceCount', cycle,
                                       pythoncom._GetInterfaceCount()) +
                   self.rrdStats.gauge('comGatewayCount', cycle,
                                       pythoncom._GetGatewayCount())):
            self.sendEvent(ev)


    def mkevt(self, name, lrec):
        """Put event in the queue to be sent to the ZenEventManager.
        """
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
                    manager=self.manager,
                    monitor=self.options.monitor)
        self.log.debug("device:%s msg:'%s'", name, lrec.message)
        return evt

    def cycleInterval(self):
        return self.eventlogCycleInterval
        

if __name__ == "__main__":
    zw = zeneventlog()
    zw.run()
