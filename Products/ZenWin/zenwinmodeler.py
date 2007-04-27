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
     Heartbeat, Status_WinSrv, Status_Wmi
from Products.ZenUtils.Utils import prepId

class zenwinmodeler(Base):
    
    evtClass = Status_WinSrv
    name = agent = "zenwinmodeler"
    evtAlertGroup = "ServiceTest"
    deviceConfig = 'getDeviceWinInfo'
    attributes = Base.attributes + ('winmodelerCycleInterval',)

    def __init__(self):
        Base.__init__(self)
        self.devices = []

    def processLoop(self):
        """For each device collect service info and send to server.
        """
        self.log.error("devices %r", self.devices);
        for name, user, passwd, sev, url in self.devices:
            if self.options.device and name != self.options.device:
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
                d = svc.callRemote('applyDataMap', url, svcs,
                                   'winservices', 'os',
                                   'Products.ZenModel.WinService')
                d.addErrback(self.error)
            except (SystemExit, KeyboardInterrupt): raise
            except pywintypes.com_error, e:
                msg = "wmi failed "
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
        dev = wmiclient.WMI(name, user, passwd)
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
        
        
    def sendFail(self, name, msg="", evtclass=Status_Wmi, sev=3):
        evt = { 'eventClass':evtclass, 
                'agent': self.agent,
                'component': '',
                'severity':sev}
        if not msg:
            msg = "wmi connection failed %s" % name
        evt['summary'] = msg
        evt['device'] = name
        self.sendEvent(evt)
        #self.log.warn(msg)
        self.log.exception(msg)
        self.failed = True

    def cycleInterval(self):
        return self.winmodelerCycleInterval
        
    def updateDevices(self, devices):
        self.devices = devices


if __name__=='__main__':
    zw = zenwinmodeler()
    zw.run()



    
