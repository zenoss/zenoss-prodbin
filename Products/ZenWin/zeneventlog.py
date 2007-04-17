#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import sys
import os
import gc
import time
import logging
import xmlrpclib
import socket
import pywintypes
import pythoncom
import wmiclient

from zenutils.Utils import basicAuthUrl
from zenutils.StatusMonitor import StatusMonitor
from StatusTest import StatusTest
from WinServiceTest import WinServiceTest
from WinEventlog import WinEventlog

class zeneventlog(StatusMonitor):

    manager = socket.getfqdn()
    
    startevt = {'eventClass':'/App/Start', 'device':socket.getfqdn(),
                'summary': 'zeneventlog started', 
                'component':'zeneventlog',
                'severity':0}
    stopevt = {'eventClass':'/App/Stop', 'device':socket.getfqdn(),
                'summary': 'zeneventlog stopped', 
                'component':'zeneventlog', 
                'severity': 4}
    heartbeat = {'eventClass':'/Heartbeat', 'device':socket.getfqdn(),
                'component': 'zeneventlog'}


    def __init__(self, config=""):
        StatusMonitor.__init__(self, config=config)
        self.configCycleInterval = 20
        self.devices = {}


    def validConfig(self):
        """let getConfig know if we have a working config or not"""
        return len(self.devices)


    def loadConfig(self):
        """get the config data from server"""
        if time.time()-self.configTime > self.configCycleInterval*60:
            self.log.info("reloading configuration")
            url = basicAuthUrl(self.username, self.password,self.winurl)
            server = xmlrpclib.Server(url)
            polltime, devices = server.getDeviceWinInfo(0, True)
            for name,user,passwd,sev,url in devices:
                try:
                    if self.checkwmi(name): 
                        self.log.info('wmi prob on %s skipping', name)
                        continue
                    if self.devices.has_key(name): continue
                    self.devices[name] = self.getWatcher(name,user,passwd,sev)
                except pywintypes.com_error:
                    self.log.exception("wmi connect failed on %s", name)
            self.configTime = time.time()



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
            if self.checkwmi(name): continue
            self.log.debug("polling %s", name)
            try:
                while 1:
                    lrec = w()
                    if not lrec.Message: continue
                    evt = self.mkevt(name, lrec)
                    self.zem.sendEvent(evt)
            except pywintypes.com_error, e:
                msg = "wmi connection failed: "
                code,txt,info,param = e
                wmsg = "%s: %s" % (abs(code), txt)
                if info:
                    wcode, source, descr, hfile, hcont, scode = info
                    scode = abs(scode)
                    if descr: wmsg = descr.strip()
                msg += wmsg
                if scode == 2147209215: # timeout
                    self.log.debug("timeout %s", name)
                elif scode == 2147023170: # rpc error
                    self.log.warn("%s %s", name, msg)
                else:
                    self.log.warn("%s %s", name, msg)
                    self.log.warn("removing %s", name)
                    baddevices.append(name)
        for name in baddevices: del self.devices[name]
        self.zem.sendEvent(self.heartbeat)
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
        evt = {}
        evt['device'] = name
        evt['eventClassKey'] = evtkey
        evt['eventGroup'] = lrec.LogFile
        evt['component'] = lrec.SourceName
        evt['ntevid'] = lrec.EventCode
        evt['summary'] = lrec.Message.strip()
        evt['agent'] = "zeneventlog"
        evt['severity'] = sev
        evt['manager'] = self.manager
        self.log.debug("device:%s msg:'%s'", name, lrec.Message)
        return evt


if __name__ == "__main__":
    zw = zeneventlog()
    zw.mainLoop()
