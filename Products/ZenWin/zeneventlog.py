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
from WMIC import WMIClient
from WinCollector import WinCollector
from Constants import TIMEOUT_CODE, RPC_ERROR_CODE

class zeneventlog(WinCollector):

    name = agent = "zeneventlog"

    eventlogCycleInterval = 5*60
    attributes = WinCollector.attributes + ('eventlogCycleInterval',)
    events = 0

    def __init__(self):
        WinCollector.__init__(self)
        self.manager = getfqdn()
        self.start()

    def fetchDevices(self, driver):
        yield self.config().callRemote('getDeviceListByMonitor',
                                       self.options.monitor)
        yield self.config().callRemote('getDeviceConfigAndWinServices', 
            driver.next())
        self.updateDevices(driver.next())
        

    def getWatcher(self, device):
        wql = """SELECT * FROM __InstanceCreationEvent where """\
            """TargetInstance ISA 'Win32_NTLogEvent' """\
            """and TargetInstance.EventType <= %d"""\
        % device.zWinEventlogMinSeverity
        wmic = WMIClient(device)
        wmic.connect()
        return wmic.watcher(wql)

        
    def processLoop(self):
        """Run WMI queries in two stages ExecQuery in semi-sync mode.
        then process results later (when they have already returned)
        """
        pythoncom.PumpWaitingMessages()
        for device in self.devices:
            if device.id in self.wmiprobs:
                self.log.debug("WMI problems on %s: skipping" % device.id)
                continue

            w = self.halfSync.boundedCall(30, self.getWatcher, device)
            self.watchers[device.id] = w
            
            self.log.debug("polling %s", device.id)
            try:
                while 1:
                    lrec = w.nextEvent()
                    if not lrec.Message:
                        continue
                    self.events += 1
                    self.sendEvent(self.mkevt(device.id, lrec))
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
                    self.log.debug("timeout %s", device.id)
                elif scode == RPC_ERROR_CODE:
                    self.log.warn("%s %s", device.id, msg)
                else:
                    self.log.warn("%s %s", device.id, msg)
                    self.log.warn("removing %s", device.id)
                    self.devices.remove(device)
        
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
