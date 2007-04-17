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

from zenutils.Utils import basicAuthUrl
from zenutils.StatusMonitor import StatusMonitor
from zenutils.SendEvent import SendEvent
from StatusTest import StatusTest
from WinServiceTest import WinServiceTest
from WinEventlog import WinEventlog

class zenwin(StatusMonitor):
    
    startevt = {'eventClass':'/App/Start', 'device':socket.getfqdn(),
                'summary': 'zenwin started', 
                'component':'zenwin',
                'severity':0}
    stopevt = {'eventClass':'/App/Stop', 'device':socket.getfqdn(),
                'summary': 'zenwin stopped', 
                'component':'zenwin', 
                'severity': 4}
    heartbeat = {'eventClass':'/Heartbeat', 'device':socket.getfqdn(),
                'component': 'zenwin'}
    

    def __init__(self, config=""):
        StatusMonitor.__init__(self, config=config)
        self.wmiprobs = []
        self.configCycleInterval = 20
        self.devices = []



    def validConfig(self):
        """let getConfig know if we have a working config or not"""
        return self.devices


    def loadConfig(self):
        """get the config data from server"""
        if time.time()-self.configTime > self.configCycleInterval*60:
            self.log.info("reloading configuration")
            url = basicAuthUrl(self.username, self.password,self.winurl)
            server = xmlrpclib.Server(url, encoding='iso-8859-1')
            devices = []
            for n,u,p,s in server.getWinServices():
	        if self.options.device and self.options.device != n: continue
                st = StatusTest(self.zem,n,u,p,s, self.options.debug)
                st.setPlugins(self.getPlugins())
                devices.append(st) 
            if devices: self.devices = devices
            self.configTime = time.time()


    def getPlugins(self):
        """Build a list of plugin instances for a device.
        """
        plugins = (WinServiceTest(), WinEventlog())
        if not self.options.load:
            #self.options.load = ['WinServiceTest', 'WinEventlog']
            self.options.load = ['WinServiceTest']
        plugins = [p for p in plugins if p.name in self.options.load]
        if not plugins:
            self.stop()
            raise SystemExit("No plugins found for list: '%s'" % (
                             ",".join(self.options.load)))
        pnames = [ p.name for p in plugins ] 
        #self.log.debug("loaded plugins: %s", ",".join(pnames))
        return plugins


    def processLoop(self):
        """Run WMI queries in two stages ExecQuery in semi-sync mode.
        then process results later (when they have already returned)
        """
        self.count = 0
        if self.options.debug:
        # in debug mode open wmi connections sequentially (ie no threads)
            for srec in self.devices:
                if not self.checkwmi(srec.name): srec.run()
                else: self.log.warn("skipping %s no wmi connection",srec.name)
        else:
        # connect to WMI service in separate thread if no ping problem detected.
            devices = self.devices[:]
            running = []
            now = time.time()
            while devices or running:
                #self.log.debug("devices:%d runing:%d",len(devices),len(running))
                running = [ srec for srec in running if not srec.done() ]
                needthreads = self.options.threads - len(running)
                while devices and needthreads > 0:
                    srec = devices.pop()
                    if not self.checkwmi(srec.name):
                        srec.start()
                        self.count += 1
                        self.log.debug("count = %d", self.count)
                        running.append(srec)
                        needthreads -= 1
                    else: 
                        self.log.warn("skipping %s no wmi connection",srec.name)
                if needthreads == 0 or not devices: time.sleep(1)
                if time.time() - now > self.cycle*2:
                    problems = ', '.join([r.name for r in running])
                    self.log.warning('%d servers (%s) still collecting '
                                     'after %d seconds, giving up',
                                     len(running),
                                     problems,
                                     self.cycle*2)
                    for r in running[:]:
                        evt = { 'eventClass': '/Status/Wmi/Conn',
                                'agent': 'zenwin',
                                'severity':'4',
                                'summary': 'Timeout failure during WMI check',
                                'device': r.name,
                                'component' : ''}
                        self.zem.sendEvent(evt)
                        running.remove(r)
                    break
                                
        #[ srec.close() for srec in self.devices ]
        sys.stdout.flush()
        self.zem.sendEvent(self.heartbeat)
        gc.collect()
        self.log.info("Com InterfaceCount: %d", pythoncom._GetInterfaceCount())
        self.log.info("Com GatewayCount: %d", pythoncom._GetGatewayCount())
        if hasattr(sys, "gettotalrefcount"):
            self.log.info("ref: %d", sys.gettotalrefcount())


    def buildOptions(self):
        StatusMonitor.buildOptions(self)
        self.parser.add_option('--threads', dest='threads', 
            default=4, type="int",
            help="number of parallel threads during collection")
        self.parser.add_option("-l", "--load", action="append", 
            dest="load", default=[],
            help="plugin name to load can have more than one")


if __name__ == "__main__":
    zw = zenwin()
    zw.mainLoop()
