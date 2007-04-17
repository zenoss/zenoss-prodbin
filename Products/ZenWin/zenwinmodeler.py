#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import os
import time
import sys
import copy
import xmlrpclib
import logging
import wmiclient
import socket
import pywintypes

from zenutils.Utils import prepId, basicAuthUrl
from zenutils.StatusMonitor import StatusMonitor
from zenutils.SendEvent import SendEvent


class zenwinmodeler(StatusMonitor):
    
    evtClass = "/Status/WinSrv"
    evtAgent = "zenwin"
    evtAlertGroup = "ServiceTest"
    startevt = {'eventClass':'/App/Start', 'device':socket.getfqdn(),
                'summary': 'zenwinmodeler started', 
                'component':'zenwinmodeler',
                'severity':0}
    stopevt = {'eventClass':'/App/Stop', 'device':socket.getfqdn(),
                'summary': 'zenwinmodeler stopped', 
                'component':'zenwinmodeler', 
                'severity': 4}
    heartbeat = {'eventClass':'/Heartbeat', 'device':socket.getfqdn(),
                'component': 'zenwinmodeler'}

    def __init__(self):
        StatusMonitor.__init__(self)
        self.configCycleInterval = 0
        self.devices = []
        self.lastStart = 0
  

    def validConfig(self):
        return len(self.devices)
   

    def loadConfig(self):
        """get the config data from server"""
        self.log.info("reloading configuration")
        url = basicAuthUrl(self.username, self.password,self.winurl)
        server = xmlrpclib.Server(url)
        self.lastStart, self.devices = \
            server.getDeviceWinInfo(self.lastStart)
        self.log.debug("laststart=%s", self.lastStart)

            
    def processLoop(self):
        """For each device collect service info and send to server.
        """
        self.lastStart = time.time()
        for name, user, passwd, sev, url in self.devices:
            if self.options.device and name != self.options.device: continue
            try:
                if self.checkwmi(name):
                    self.log.warn("skipping %s has bad wmi state", name)
                    continue
                self.log.info("collecting from %s using user %s", name, user)
                svcs = self.getServices(name, user, passwd)
                if not svcs: 
                    self.log.warn("failed collecting from %s", name)
                    continue
                url = basicAuthUrl(self.username, self.password, url)
                server = xmlrpclib.Server(url)
                server.applyDataMap(svcs,"winservices","os",
                                    "Products.ZenModel.WinService")
            except (SystemExit, KeyboardInterrupt): raise
            except pywintypes.com_error, e:
                msg = "wmi failed "
                code,txt,info,param = e
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
            sdata = {'id':prepId(svc.name), 'setServiceClass':
                     {'name':svc.name, 'description':svc.caption}}
            for att in attrs:
                if att in ("name", "caption"): continue
                sdata[att] = getattr(svc,att,"")
            data.append(sdata)
        return data
        
        
    def sendFail(self, name, msg="", evtclass="/Status/Wmi", sev=3):
        evt = { 'eventClass':evtclass, 
                'agent': 'zenwinmodeler', 'component': '',
                'severity':sev}
        if not msg:
            msg = "wmi connection failed %s" % name
        evt['summary'] = msg
        evt['device'] = name
        self.zem.sendEvent(evt)
        #self.log.warn(msg)
        self.log.exception(msg)
        self.failed = True



if __name__=='__main__':
    zw = zenwinmodeler()
    zw.mainLoop()



    
