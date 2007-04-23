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

from twisted.internet import reactor, defer

import Globals
from WinCollector import WinCollector as Base
from Products.ZenHub.services import WmiConfig
from Products.ZenEvents.ZenEventClasses import Heartbeat, Status_Wmi_Conn

from StatusTest import StatusTest
from WinServiceTest import WinServiceTest
from WinEventlog import WinEventlog

class zenwin(Base):

    name = agent = "zenwin"
    deviceConfig  = 'getWinServices'

    def __init__(self):
        Base.__init__(self)
        self.wmiprobs = []
        self.devices = []


    def getPlugins(self):
        """Build a list of plugin instances for a device.
        """
        plugins = (WinServiceTest(), WinEventlog())
        if not self.options.load:
            self.options.load = ['WinServiceTest']
        plugins = [p for p in plugins if p.name in self.options.load]
        if not plugins:
            self.stop()
            raise SystemExit("No plugins found for list: '%s'" % (
                             ",".join(self.options.load)))
        pnames = [p.name for p in plugins] 
        return plugins


    def processLoop(self, unused=None):
        """Run WMI queries in two stages ExecQuery in semi-sync mode.
        then process results later (when they have already returned)
        """
        self.count = 0
        if self.options.debug:
            # in debug mode open wmi connections sequentially (ie no threads)
            for srec in self.devices:
                if srec.name not in self.wmiprobs:
                    srec.run()
                else:
                    self.log.warn("skipping %s no wmi connection",srec.name)
        else:
            # connect to WMI service in separate thread if no
            # ping problem detected.
            devices = self.devices[:]
            running = []
            now = time.time()
            while devices or running:
                self.log.debug("devices:%d runing:%d",
                               len(devices), len(running))
                running = [ srec for srec in running if not srec.done() ]
                needthreads = self.options.threads - len(running)
                while devices and needthreads > 0:
                    srec = devices.pop()
                    if srec.name not in self.wmiprobs:
                        srec.start()
                        self.count += 1
                        self.log.debug("count = %d", self.count)
                        running.append(srec)
                        needthreads -= 1
                    else: 
                        self.log.warn("skipping %s no wmi connection",srec.name)
                if needthreads == 0 or not devices:
                    time.sleep(1)
                if time.time() - now > self.cycleInterval*2:
                    problems = ', '.join([r.name for r in running])
                    self.log.warning('%d servers (%s) still collecting '
                                     'after %d seconds, giving up',
                                     len(running),
                                     problems,
                                     self.cycleInterval*2)
                    for r in running[:]:
                        evt = { 'eventClass': Status_Wmi_Conn,
                                'agent': self.agent,
                                'severity':'4',
                                'summary': 'Timeout failure during WMI check',
                                'device': r.name,
                                'component' : ''}
                        self.sendEvent(evt)
                        running.remove(r)
                    break

        #[ srec.close() for srec in self.devices ]
        sys.stdout.flush()
        self.sendEvent(self.heartbeat)
        import gc; gc.collect()
        self.log.info("Com InterfaceCount: %d", pythoncom._GetInterfaceCount())
        self.log.info("Com GatewayCount: %d", pythoncom._GetGatewayCount())
        if hasattr(sys, "gettotalrefcount"):
            self.log.info("ref: %d", sys.gettotalrefcount())


    def updateDevices(self, devices):
        config = []
        for n,u,p,s in devices:
            if self.options.device and self.options.device != n: continue
            st = StatusTest(self, n, u, p, s, self.options.debug)
            st.setPlugins(self.getPlugins())
            config.append(st) 
        if devices:
            self.devices = config
    
    def buildOptions(self):
        Base.buildOptions(self)
        self.parser.add_option('--threads',
                               dest='threads', 
                               default=4,
                               type="int",
                               help="number of parallel threads "
                                    "during collection")
        self.parser.add_option("-l", "--load",
                               action="append", 
                               dest="load",
                               default=[],
                               help="plugin name to load can "
                                    "have more than one")


if __name__ == "__main__":
    zw = zenwin()
    zw.run()
