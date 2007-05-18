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

import os
import time
import sys
import logging
import wmiclient
from socket import getfqdn
import pywintypes


import Globals
from WinCollector import WinCollector as Base
from Products.ZenEvents.ZenEventClasses import \
     Heartbeat, Status_WinService, Status_Wmi
from Products.ZenUtils.Utils import prepId

from Products.ZenEvents import Event

class zenwinmodeler(Base):
    
    evtClass = Status_WinService
    name = agent = "zenwinmodeler"
    evtAlertGroup = "ServiceTest"
    deviceConfig = 'getDeviceWinInfo'
    winmodelerCycleInterval = 20*60
    attributes = Base.attributes + ('winmodelerCycleInterval',)

    def __init__(self):
        Base.__init__(self)
        self.devices = []
        self.lastRead = {}
        self.start()

    def remote_deleteDevice(self, device):
        self.devices = [d for d in self.devices if d.name != device]
    
    def processLoop(self):
        """For each device collect service info and send to server.
        """
        self.log.error("devices %r", self.devices);
        for lastChange, name, user, passwd, sev, url in self.devices:
            if self.options.device and name != self.options.device:
                continue
            if self.lastRead.get(name, 0) > lastChange:
                self.log.debug('Skipping %s: recently checked' % name)
                continue
            try:
                if name in self.wmiprobs:
                    self.log.warn("skipping %s has bad wmi state", name)
                    continue
                self.log.info("collecting from %s using user %s", name, user)
                svcs = self.getServices(name, user, passwd)
                if not svcs: 
                    self.log.warn("failed collecting from %s", name)
                    continue
                svc = self.configService()
                self.lastRead[name] = time.time()
                d = svc.callRemote('applyDataMap', url, svcs,
                                   'winservices', 'os',
                                   'Products.ZenModel.WinService')
                d.addErrback(self.error)
            except (SystemExit, KeyboardInterrupt): raise
            except pywintypes.com_error, e:
                msg = "WMI error talking to %s " % name
                code, txt, info, param = e
                wmsg = "%s: %s" % (abs(code), txt)
                if info:
                    wcode, source, descr, hfile, hcont, scode = info
                    scode = abs(scode)
                    if descr: wmsg = descr.strip()
                msg += "%d: %s" % (scode, wmsg)
                self.sendFail(name, msg)
            except:
                self.sendFail(name)

   
    def getServices(self, name, user, passwd):
        """Collect the service info and build datamap using WMI.
        """
        data = []
        attrs = ("acceptPause","acceptStop","name","caption",
                 "pathName","serviceType","startMode","startName")
        dev = wmiclient.WMI(*map(str, (name, user, passwd)))
        dev.connect()
        wql = "select %s from Win32_Service" % (",".join(attrs))
        svcs = dev.query(wql)
        self.log.debug("query='%s'", wql)
        for svc in svcs:
            sdata = {'id':prepId(svc.name),
                     'setServiceClass': {'name':svc.name,
                                         'description':svc.caption}}
            for att in attrs:
                if att in ("name", "caption"): continue
                sdata[att] = getattr(svc,att,"")
            data.append(sdata)
        return data
        
        
    def sendFail(self, name, msg="", evtclass=Status_Wmi, sev=Event.Warning):
        if not msg:
            msg = "WMI connection failed %s" % name
            sev = Event.Error
        evt = dict(summary=msg,
                   eventClass=evtclass, 
                   device=name,
                   severity=sev,
                   agent=self.agent)
        self.sendEvent(evt)
        self.log.exception(msg)
        self.failed = True

    def cycleInterval(self):
        return self.winmodelerCycleInterval
        
    def updateDevices(self, devices):
        self.log.info("Updating devices")
        self.devices = devices


if __name__=='__main__':
    zw = zenwinmodeler()
    zw.run()



    
