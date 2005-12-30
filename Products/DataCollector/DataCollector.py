#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""DataCollector

Collects data from devices and puts it into objects in the DMD
data is passed through 3 queues in this system:

self.devices -> self.clients -> self.deviceMaps

self.devices is a list of DMD devices on which we will collect
self.clients is the list of active CollectorClients
self.deviceMaps is the list of results received from remote devices

$Id: DataCollector.py,v 1.8 2003/12/18 23:07:44 edahl Exp $"""

__version__ = "$Revision: 1.8 $"[11:-2]

import sys
import os
import time
import types
import Queue

from twisted.internet import reactor

import Globals
import transaction

from Products.ZenUtils.ZeoPoolBase import ZeoPoolBase
from Products.ZenUtils.Utils import importClass

from ApplyDataMap import ApplyDataMap, ApplyDataMapThread

import CollectorClient
import SshClient
import TelnetClient
from Exceptions import *

defaultProtocol = "ssh"
defaultPort = 22
defaultParallel = 10

class DataCollector(ZeoPoolBase):
    
    def __init__(self, noopts=0,app=None):
        ZeoPoolBase.__init__(self,noopts)
        if not noopts: self.processOptions()

        self.cycletime = self.options.cycletime*60

        self.app = self.dmd = None
        self.clients = {}
        self.commandPlugins = {} 
        self.snmpPlugins = []
        self.deviceMaps = {}
        self.devicegen = None

        self.loadPlugins()

        if app or self.options.debug:
            self.log.debug("in debug mode starting apply in main thread.")
            self.applyData = ApplyDataMap()
        else:
            self.applyData = ApplyDataMapThread(self.getConnection())
            self.applyData.start()
 


    def loadPlugins(self):
        """Load plugins from the plugin directory.
        """
        pdir = os.path.join(os.path.dirname(__file__), "plugins")
        sys.path.append(pdir)
        self.log.info("loading collector plugins from:%s", pdir)
        for path, dirname, filenames in os.walk(pdir):
            def filef(n): return not n.startswith("_") and n.endswith(".py")
            for filename in filter(filef, filenames):
                try:
                    modpath = os.path.join(path,filename[:-3]).replace("/",".")
                    self.log.info("loading:%s", modpath)
                    const = importClass(modpath)
                    plugin = const()
                    if plugin.transport == "command":
                        self.commandPlugins[plugin.command] = plugin
                    elif plugin.transport == "snmp":
                        self.snmpPlugin.append(plugin)
                    else:
                        self.log.warn("skipped:%s unknown transport:%s", 
                                       plugin.name(), plugin.transport)
                except ImportError, e:
                    self.log.warn(e)


    def collectDevices(self, deviceroot):
        """Main processing loop collecting command data from devices.
        """
        if type(deviceroot) == types.StringType:
            deviceroot = self.dmd.Devices.getOrganizer(deviceroot)
        self.devicegen = deviceroot.getSubDevicesGen()
        for i, device in enumerate(self.devicegen):
            if i >= self.options.parallel: break
            client = self.collectDevice(device)
        if i > 0: 
            self.log.debug("reactor start multi-device")
            reactor.run(False)
        else: self.log.warn("no valid clients found")
            
        

    def collectDevice(self, device):
        """Initiate collection from a single device.
        """
        if type(device) == types.StringType:
            device = self.dmd.Devices.findDevice(self.options.device)
            if not device: 
                raise DataCollectorError(
                        "device %s not found" % self.options.device)

        hostname = device.getId()
        client = None
        commands = self.getCommands(device)
        if not commands:
            self.log.warn("no commands found for %s" % hostname)
            return 
        protocol = getattr(device, 
                    'zCommandProtocol', defaultProtocol)
        commandPort = getattr(device, 'zCommandPort', defaultPort)
        if protocol == "ssh": 
            client = SshClient.SshClient(hostname, commandPort, 
                                options=self.options,
                                commands=commands, device=device, 
                                datacollector=self, log=self.log)
        elif protocol == 'telnet':
            if commandPort == 22: commandPort = 23 #set default telnet
            client = TelnetClient.TelnetClient(hostname, commandPort,
                                options=self.options,
                                commands=commands, device=device, 
                                datacollector=self, log=self.log)
        else:
            self.log.warn("unknown protocol %s for device %s" 
                                       % (protocol, hostname))
        if client: self.clients[client] = 1
        if self.options.device: 
            self.log.debug("reactor start single-device")
            reactor.run(False)
        return client


    def getCommands(self, device):
        """Build a list of active plugins for a device.  
        Returns a list of commands to be run.
        """
        aqIgnorePlugins = getattr(device, 'zCommandIgnorePlugins', [])
        aqCollectPlugins = getattr(device, 'zCommandCollectPlugins', [])
        plugins = []
        for plugin in self.commandPlugins.values():
            pname = plugin.name()
            if not plugin.condition(device, self.log):
                self.log.debug("condition failed %s on device %s", 
                                pname, device.id)
            elif (pname in self.options.ignorePlugins or
                pname in aqIgnorePlugins):
                self.log.debug("ignore %s on device %s" % (pname, device.id))
            elif (pname in self.options.collectPlugins or
                    pname in aqCollectPlugins):
                self.log.debug("collect %s on device %s" 
                                    % (pname, device.id))
                plugins.append(plugin)
            elif not (self.options.collectPlugins or aqCollectPlugins):
                self.log.debug("collect %s on device %s" 
                                    % (pname, device.id))
                plugins.append(plugin)
        commands = map(lambda x: x.command, plugins)
        self.log.debug("%s cmds: '%s'", device.getId(), "', '".join(commands))
        return commands
             
    
    def clientFinished(self, collectorClient):
        """Process the return values from a device. 
        """
        try:
            nodevices = False
            self.log.debug("client for %s finished collecting",
                            collectorClient.hostname)
            datamaps = []
            for command, results in collectorClient.getResults():
                try:
                    device = collectorClient.device
                    if not self.commandPlugins.has_key(command): continue
                    plugin = self.commandPlugins[command]
                    datamaps.append(plugin.process(device, results, self.log))
                except(SystemExit, KeyboardInterrupt): raise
                except:
                    self.log.exception("parsing command:%s", command)
            self.applyData.applyDataMaps(device, datamaps)
            try:
                if not self.devicegen: raise StopIteration
                device = self.devicegen.next()
                self.collectDevice(device)
            except StopIteration:
                nodevices = True
        finally:
            del self.clients[collectorClient]
            self.log.debug("clients=%s nodevices=%s",
                            len(self.clients),nodevices)
            if not self.clients and nodevices: 
                self.log.debug("reactor stop")
                reactor.stop()


    def buildOptions(self):
        ZeoPoolBase.buildOptions(self)
        self.parser.add_option('--debug',
                dest='debug', action="store_true",
                help="don't fork threads for processing")
        self.parser.add_option('--parallel', dest='parallel', 
                type='int', default=defaultParallel,
                help="number of devices to collect from in parallel")
        self.parser.add_option('--cycletime',
                dest='cycletime',default=60,type='int',
                help="run collection every x minutes")
        self.parser.add_option('--ignore',
                dest='ignorePlugins',default="",
                help="Comma separated list of collection maps to ignore")
        self.parser.add_option('--collect',
                dest='collectPlugins',default="",
                help="Comma separated list of collection maps to use")
        self.parser.add_option('-p', '--path',
                dest='path',
                help="start path for collection ie /NetworkDevices")
        self.parser.add_option('-d', '--device',
                dest='device',
                help="fully qualified device name ie www.confmon.com")
        self.parser.add_option('-a', '--collectAge',
                dest='collectAge',
                default=0,
                type='int',
                help="don't collect from devices whos collect date " +
                        "is with in this many minutes")
        TelnetClient.buildOptions(self.parser, self.usage)

    
    def processOptions(self):
        if not self.options.path and not self.options.device:
            raise SystemExit("no device or path specified must have one!")
        if self.options.ignorePlugins and self.options.collectPlugins:
            raise SystemExit("--ignore and --collect are mutually exclusive")
        if self.options.ignorePlugins:
            self.options.ignorePlugins = self.options.ignorePlugins.split(',')
        if self.options.collectPlugins:
            self.options.collectPlugins = self.options.collectPlugins.split(',')


    def opendmd(self):
        if not self.dmd:
            self.app = self.getConnection()
            self.dmd = self.app.zport.dmd


    def closedmd(self):
        if self.dmd:
            self.dmd = None
            self.app = None
            self.closeAll()


    def mainLoop(self):
        while 1:
            startLoop = time.time()
            runTime = 0
            try:
                try:
                    self.log.info("starting collector loop")
                    self.app._p_jar.sync()
                    self.collectDevices(self.options.path)
                    self.log.info("ending collector loop")
                finally:
                    transaction.abort()
                runTime = time.time()-startLoop
                self.log.info("loop time = %0.2f seconds",runTime)
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("problem in main loop")
            if runTime < self.cycletime:
                time.sleep(self.cycletime - runTime)


    def sigTerm(self, signum, frame):
        self.log.info("stopping...")
        self.applyData.done = True
        #wait for apply thread to close
        if hasattr(self.applyData, 'join'):
            self.applyData.join(10)  
        self.closedmd()
        ZeoPoolBase.sigTerm(self, signum, frame)



    def main(self):
        self.opendmd()
        if self.options.device:
            self.collectDevice(self.options.device)
        elif not self.options.cycle:
            self.collectDevices(self.options.path)
        else:
            self.mainLoop()
        transaction.abort()
                    


if __name__ == '__main__':
    dc = DataCollector()
    dc.main()
