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

import time
import types
import re
import socket

import Globals
import transaction
import DateTime
from twisted.internet import reactor

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenEvents.ZenEventClasses import Heartbeat

from ApplyDataMap import ApplyDataMap, ApplyDataMapThread
import SshClient
import TelnetClient
import SnmpClient
import PortscanClient

from Exceptions import *

defaultPortScanTimeout = 5
defaultParallel = 1
defaultProtocol = "ssh"
defaultPort = 22
defaultStartSleep = 10 * 60

from Plugins import loadPlugins

class ZenModeler(ZCmdBase):

    generateEvents = True
    
    def __init__(self,noopts=0,app=None,single=False,
                 threaded=None,keeproot=False):
        ZCmdBase.__init__(self, noopts, app, keeproot)
        
        if self.options.daemon:
            if self.options.now:
                self.log.debug("Run as a daemon, starting immediately.")
            else:
                self.log.debug("Run as a daemon, waiting %s sec to start." % defaultStartSleep)
                time.sleep(defaultStartSleep)
                self.log.debug("Run as a daemon, slept %s sec, starting now." % defaultStartSleep)
        else:
            self.log.debug("Run in foreground, starting immediately.")
            
        self.single = single
        if self.options.device:
            self.single = True
        self.threaded = threaded
        if self.threaded is None:
            self.threaded = not self.options.nothread
        self.cycletime = self.options.cycletime*60
        self.collage = self.options.collage / 1440.0
        self.clients = []
        self.finished = []
        self.collectorPlugins = {}
        self.devicegen = None
        self.loadPlugins()
        self.slowDown = False
        if self.threaded and not self.single:
            self.log.info("starting apply in separate thread.")
            self.applyData = ApplyDataMapThread(self, self.getConnection())
            self.applyData.start()
        else:
            self.log.debug("in debug mode starting apply in main thread.")
            self.applyData = ApplyDataMap(self)

    def loadPlugins(self):
        """Load plugins from the plugin directory.
        """
        self.collectorPlugins = loadPlugins(self.dmd)

    
    def selectPlugins(self, device, transport):
        """Build a list of active plugins for a device.  
        """
        names = getattr(device, 'zCollectorPlugins', [])
        result = []
        collectTest = lambda x: False
        ignoreTest = lambda x: False
        if self.options.collectPlugins:
            collectTest = re.compile(self.options.collectPlugins).search
        elif self.options.ignorePlugins:
            ignoreTest = re.compile(self.options.ignorePlugins).search
        for plugin in self.collectorPlugins.values():
            if plugin.transport != transport:
                continue
            name = plugin.name()
            try:
                if not plugin.condition(device, self.log):
                    self.log.debug("condition failed %s on %s",name,device.id) 
                elif ignoreTest(name):
                    self.log.debug("ignoring %s on %s",name, device.id)
                elif name in names and not self.options.collectPlugins:
                    self.log.debug("using %s on %s",name, device.id)
                    result.append(plugin)
                elif collectTest(name):
                    self.log.debug("--collect %s on %s", name, device.id)
                    result.append(plugin)
                else:
                    self.log.debug("skipping %s for %s", name, device.id)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("failed to select plugin %s", name)
        return result
             
    
    def resolveDevice(self, device):
        """If device is a string look it up in the dmd.
        """
        if type(device) == types.StringType:
            dname = device
            device = self.dmd.Devices.findDevice(device)
            if not device:
                raise DataCollectorError("device %s not found" % dname)
        return device


    def collectDevice(self, device):
        """Collect data from a single device.
        """
        clientTimeout = getattr(device, 'zCollectorClientTimeout', 180)
        ip = device.getManageIp()
        if not ip:
            ip = device.setManageIp()
        timeout = clientTimeout + time.time()
        self.cmdCollect(device, ip, timeout)
        self.snmpCollect(device, ip, timeout)
        self.portscanCollect(device, ip, timeout)
        

    def cmdCollect(self, device, ip, timeout):
        """Start command collection client.
        """
        client = None
        clientType = 'snmp'
        hostname = device.id
        try:
            plugins = self.selectPlugins(device,"command")
            commands = map(lambda x: (x.name(), x.command), plugins)
            if not commands:
                self.log.info("no cmd plugins found for %s" % hostname)
                return 
            protocol = getattr(device, 'zCommandProtocol', defaultProtocol)
            commandPort = getattr(device, 'zCommandPort', defaultPort)
            if protocol == "ssh": 
                client = SshClient.SshClient(hostname, ip, commandPort, 
                                    options=self.options,
                                    commands=commands, device=device, 
                                    datacollector=self)
                clientType = 'ssh'
                self.log.info('using ssh collection device %s' % hostname)
            elif protocol == 'telnet':
                if commandPort == 22: commandPort = 23 #set default telnet
                client = TelnetClient.TelnetClient(hostname, ip, commandPort,
                                    options=self.options,
                                    commands=commands, device=device, 
                                    datacollector=self)
                clientType = 'telnet'
                self.log.info('using telnet collection device %s' % hostname)
            else:
                self.log.warn("unknown protocol %s for device %s",
                                protocol, hostname)
            if not client: 
                self.log.warn("cmd client creation failed")
            else:
                self.log.info("plugins: %s", 
                    ", ".join(map(lambda p: p.name(), plugins)))
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("error opening cmdclient")
        self.addClient(client, timeout, clientType, device.id)

    
    def snmpCollect(self, device, ip, timeout):
        """Start snmp collection client.
        """
        client = None
        try:
            plugins = []
            hostname = device.id
            plugins = self.selectPlugins(device,"snmp")
            if not plugins:
                self.log.info("no snmp plugins found for %s" % hostname)
                return 
            if self.checkCollection(device):
                self.log.info('snmp collection device %s' % hostname)
                self.log.info("plugins: %s", 
                              ", ".join(map(lambda p: p.name(), plugins)))
                client = SnmpClient.SnmpClient(device.id,
                                               ip,
                                               self.options, 
                                               device,
                                               self,
                                               plugins)
            if not client or not plugins: 
                self.log.warn("snmp client creation failed")
                return
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("error opening snmpclient")
        self.addClient(client, timeout, 'snmp', device.id)

    def addClient(self, obj, timeout, clientType, name):
        if obj:
            obj.timeout = timeout
            self.clients.append(obj)
            obj.run()
        else:
            self.log.warn('Unable to create a %s client for %s',
                          clientType, name)
            

    # XXX double-check this, once the implementation is in place
    def portscanCollect(self, device, ip, timeout):
        """
        Start portscan collection client.
        """
        client = None
        try:
            plugins = []
            hostname = device.id
            plugins = self.selectPlugins(device, "portscan")
            if not plugins:
                self.log.info("no portscan plugins found for %s" % hostname)
                return
            if self.checkCollection(device):
                self.log.info('portscan collection device %s' % hostname)
                self.log.info("plugins: %s",
                    ", ".join(map(lambda p: p.name(), plugins)))
                client = PortscanClient.PortscanClient(device.id, ip,
                    self.options, device, self, plugins)
            if not client or not plugins:
                self.log.warn("portscan client creation failed")
                return
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("error opening portscanclient")
        self.addClient(client, timeout, 'portscan', device.id)


    def checkCollection(self, device):
        age = device.getSnmpLastCollection() + self.collage
        if device.getSnmpStatusNumber() > 0 and age >= DateTime.DateTime():
            self.log.info("skipped collection of %s" % device.getId())
            return False
        return True


    def clientFinished(self, collectorClient):
        """Callback that processes the return values from a device. 
        """
        try:
            self.log.debug("client for %s finished collecting",
                            collectorClient.hostname)
            device = collectorClient.device
            self.applyData.processClient(device, collectorClient)
        finally:
            try:
                self.clients.remove(collectorClient)
                self.finished.append(collectorClient)
            except ValueError:
                self.log.warn("client %s not found in active clients",
                              collectorClient.hostname)
        self.fillCollectionSlots()


    def checkStop(self):
        "if there's nothing left to do, maybe we should terminate"
        if self.clients: return
        if self.devicegen: return

        if self.start:
            runTime = time.time() - self.start
            self.log.info("scan time: %0.2f seconds", runTime)
            self.start = None
            if self.options.cycle:
                evt = dict(eventClass=Heartbeat,
                           component='zenmodeler',
                           device=socket.getfqdn(),
                           timeout=self.cycletime*3)
                if self.dmd:
                    self.dmd.ZenEventManager.sendEvent(evt)
            else:
                self.stop()

    def fillCollectionSlots(self):
        """If there are any free collection slots fill them up
        """
        count = len(self.clients)
        while (count < self.options.parallel and
               self.devicegen and not self.slowDown):
            try:
                device = self.devicegen.next()
                if (device.productionState <= 
                    getattr(device,'zProdStateThreshold',0)): 
                    self.log.info("skipping %s production state too low",
                                  device.id)
                    continue
                # just collect one device, and let the timer add more
                self.collectDevice(device)
            except StopIteration:
                self.devicegen = None
            break

        update = len(self.clients)
        if update != count and update != 1:
            self.log.info('Running %d clients', update)
        self.checkStop()


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--debug',
                dest='debug', action="store_true", default=False,
                help="don't fork threads for processing")
        self.parser.add_option('--nothread',
                dest='nothread', action="store_true", default=False,
                help="do not use threads when applying updates")
        self.parser.add_option('--parallel', dest='parallel', 
                type='int', default=defaultParallel,
                help="number of devices to collect from in parallel")
        self.parser.add_option('--cycletime',
                dest='cycletime',default=720,type='int',
                help="run collection every x minutes")
        self.parser.add_option('--ignore',
                dest='ignorePlugins',default="",
                help="Comma separated list of collection maps to ignore")
        self.parser.add_option('--collect',
                dest='collectPlugins',default="",
                help="Comma separated list of collection maps to use")
        self.parser.add_option('-p', '--path', dest='path',
                help="start path for collection ie /NetworkDevices")
        self.parser.add_option('-d', '--device', dest='device',
                help="fully qualified device name ie www.confmon.com")
        self.parser.add_option('-a', '--collage',
                dest='collage', default=0, type='float',
                help="do not collect from devices whose collect date " +
                        "is within this many minutes")
        self.parser.add_option('--writetries',
                dest='writetries',default=2,type='int',
                help="number of times to try to write if a "
                     "read conflict is found")
        self.parser.add_option("-F", "--force",
                    dest="force", action='store_true', default=False,
                    help="force collection of config data " 
                         "(even without change to the device)")
        self.parser.add_option('--portscantimeout', dest='portscantimeout', 
                type='int', default=defaultPortScanTimeout,
                help="time to wait for connection failures when port scanning")
        self.parser.add_option('--now', 
                dest='now', action="store_true", default=False,
                help="start daemon now, do not sleep before starting")
        TelnetClient.buildOptions(self.parser, self.usage)
    

    
    def processOptions(self):
        if not self.options.path and not self.options.device:
            self.options.path = "/Devices"
        if self.options.ignorePlugins and self.options.collectPlugins:
            raise SystemExit("--ignore and --collect are mutually exclusive")


    def timeoutClients(self):
        reactor.callLater(1, self.timeoutClients)
        active = []
        for client in self.clients:
            if client.timeout < time.time():
                self.log.warn("client %s timeout", client.hostname)
                self.finished.append(client)
            else:
                active.append(client)
        self.clients = active
        self.fillCollectionSlots()
        self.checkStop()
                

    def reactorLoop(self):
        reactor.startRunning(installSignalHandlers=False)
        while reactor.running:
            try:
                while reactor.running:
                    reactor.runUntilCurrent()
                    reactor.doIteration(0)
                    timeout = reactor.timeout()
                    self.slowDown = timeout < 0.01
                    reactor.doIteration(timeout)
            except:
                self.log.exception("Unexpected error in main loop.")
        

    def stop(self):
        """Stop ZenModeler make sure reactor is stopped, join with 
        applyData thread and close the zeo connection.
        """
        self.log.info("stopping...")
        self.applyData.stop()
        transaction.abort()
        reactor.callLater(0., reactor.crash)


    def mainLoop(self):
        if self.options.cycle:
            reactor.callLater(self.cycletime, self.mainLoop)

        if self.clients:
            self.log.error("modeling cycle taking too long")
            return

        self.log.info("starting collector loop")
        self.app._p_jar.sync()
        self.start = time.time()
        if self.options.device:
            self.log.info("collecting for device %s", self.options.device)
            self.devicegen = iter([self.resolveDevice(self.options.device)])
        else:
            self.log.info("collecting for path %s", self.options.path)
            root = self.dmd.Devices.getOrganizer(self.options.path)
            self.devicegen = root.getSubDevicesGen()
        self.fillCollectionSlots()
        

    def sigTerm(self, *unused):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, *unused)
        except SystemExit:
            pass

    def main(self):
        self.finished = []
        self.mainLoop()
        self.timeoutClients()

    def collectSingle(self, device):
        self.finished = []
        self.start = time.time()
        self.devicegen = iter([self.resolveDevice(device)])
        self.fillCollectionSlots()
        self.timeoutClients()

if __name__ == '__main__':
    dc = ZenModeler()
    dc.processOptions()
    dc.main()
    dc.reactorLoop()
