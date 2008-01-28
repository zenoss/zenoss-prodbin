##########################################################################
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
import Globals
import DateTime
from twisted.internet import reactor
from twisted.internet.defer import succeed

from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.Utils import unused
from Products.ZenEvents.ZenEventClasses import Heartbeat

import PythonClient
import SshClient
import TelnetClient
import SnmpClient
import PortscanClient

defaultPortScanTimeout = 5
defaultParallel = 1
defaultProtocol = "ssh"
defaultPort = 22
defaultStartSleep = 10 * 60

from Products.DataCollector import DeviceProxy
from Products.DataCollector import Plugins
# needed for pb to work
unused(DeviceProxy)
unused(Plugins)

class ZenModeler(PBDaemon):

    name = 'zenmodeler'
    initialServices = PBDaemon.initialServices + ['ModelerService']

    generateEvents = True
    
    def __init__(self,noopts=0,app=None,single=False,
                 threaded=None,keeproot=False):
        PBDaemon.__init__(self)
        # FIXME: cleanup --force option #2660
        self.options.force = True
        if self.options.daemon:
            if self.options.now:
                self.log.debug("Run as a daemon, starting immediately.")
            else:
                self.log.debug("Run as a daemon, waiting %s sec to start." %
                               defaultStartSleep)
                time.sleep(defaultStartSleep)
                self.log.debug("Run as a daemon, slept %s sec, starting now." %
                               defaultStartSleep)
        else:
            self.log.debug("Run in foreground, starting immediately.")

        self.start = None
        self.rrdStats = DaemonStats()
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
        self.devicegen = None
        self.slowDown = False

    def reportError(self, error):
        self.log.error("Error occured: %s", error)

    def connected(self):
        self.log.debug("Connected to ZenHub")
        d = self.configure()
        d.addCallback(self.heartbeat)
        d.addErrback(self.reportError)
        d.addCallback(self.main)

    def configure(self):
        # add in the code to fetch cycle time, etc.
        return succeed(None)

    def config(self):
        "Get the ModelerService"
        return self.services.get('ModelerService', FakeRemote())

    def selectPlugins(self, device, transport):
        """Build a list of active plugins for a device.  
        """
        plugins = [loader.create() for loader in device.plugins]
        result = []
        collectTest = lambda x: False
        ignoreTest = lambda x: False
        if self.options.collectPlugins:
            collectTest = re.compile(self.options.collectPlugins).search
        elif self.options.ignorePlugins:
            ignoreTest = re.compile(self.options.ignorePlugins).search
        for plugin in plugins:
            if plugin.transport != transport:
                continue
            name = plugin.name()
            if ignoreTest(name):
                self.log.debug("ignoring %s on %s",name, device.id)
            elif collectTest(name):
                self.log.debug("--collect %s on %s", name, device.id)
                result.append(plugin)
            else:
                self.log.debug("using %s on %s",name, device.id)
                result.append(plugin)
        return result
             
    
    def collectDevice(self, device):
        """Collect data from a single device.
        """
        clientTimeout = getattr(device, 'zCollectorClientTimeout', 180)
        ip = device.manageIp
        timeout = clientTimeout + time.time()
        self.pythonCollect(device, ip, timeout)
        self.cmdCollect(device, ip, timeout)
        self.snmpCollect(device, ip, timeout)
        self.portscanCollect(device, ip, timeout)


    def pythonCollect(self, device, ip, timeout):
        """Start local collection client.
        """
        client = None
        try:
            plugins = self.selectPlugins(device, "python")
            if not plugins:
                self.log.info("no python plugins found for %s" % device.id)
                return
            if self.checkCollection(device):
                self.log.info('python collection device %s' % device.id)
                self.log.info("plugins: %s",
                        ", ".join(map(lambda p: p.name(), plugins)))
                client = PythonClient.PythonClient(device, self, plugins)
            if not client or not plugins:
                self.log.warn("python client creation failed")
                return
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("error opening pythonclient")
        self.addClient(client, timeout, 'python', device.id)


    def cmdCollect(self, device, ip, timeout):
        """Start command collection client.
        """
        client = None
        clientType = 'snmp'
        hostname = device.id
        try:
            plugins = self.selectPlugins(device,"command")
            if not plugins:
                self.log.info("no cmd plugins found for %s" % hostname)
                return 
            protocol = getattr(device, 'zCommandProtocol', defaultProtocol)
            commandPort = getattr(device, 'zCommandPort', defaultPort)
            if protocol == "ssh": 
                client = SshClient.SshClient(hostname, ip, commandPort, 
                                    options=self.options,
                                    plugins=plugins, device=device, 
                                    datacollector=self)
                clientType = 'ssh'
                self.log.info('using ssh collection device %s' % hostname)
            elif protocol == 'telnet':
                if commandPort == 22: commandPort = 23 #set default telnet
                client = TelnetClient.TelnetClient(hostname, ip, commandPort,
                                    options=self.options,
                                    plugins=plugins, device=device, 
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
            if not device.zSnmpMonitorIgnore:
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
            obj.timedOut = False
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
            hostname = device.id
            plugins = self.selectPlugins(device, "portscan")
            if not plugins:
                self.log.info("no portscan plugins found for %s" % hostname)
                return
            if self.checkCollection(device):
                self.log.info('portscan collection device %s' % hostname)
                self.log.info("plugins: %s",
                    ", ".join(map(lambda p: p.name(), plugins)))
                client = PortscanClient.PortscanClient(device.id,
                                                       ip,
                                                       self.options,
                                                       device,
                                                       self,
                                                       plugins)
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
            self.log.info("skipped collection of %s" % device.id)
            return False
        return True


    def clientFinished(self, collectorClient):
        """Callback that processes the return values from a device. 
        """
        device = collectorClient.device
        self.log.debug("client for %s finished collecting", device.id)
        def processClient(driver):
            self.log.debug("processing data for device %s", device.id)
            devchanged = False
            maps = []
            for plugin, results in collectorClient.getResults():
                self.log.debug("processing plugin %s on device %s",
                               plugin.name(), device.id)
                if not results: 
                    self.log.warn("plugin %s no results returned",
                                  plugin.name())
                    continue

                results = plugin.preprocess(results, self.log)
                datamaps = plugin.process(device, results, self.log)

                # allow multiple maps to be returned from one plugin
                if type(datamaps) not in (types.ListType, types.TupleType):
                    datamaps = [datamaps,]
                if datamaps:
                    maps += [m for m in datamaps if m]
            if maps:
                yield self.config().callRemote('applyDataMaps', device.id, maps)
                if driver.next():
                    devchanged = True
            if devchanged:
                self.log.info("changes applied")
            else:
                self.log.info("no change detected")
            yield self.config().callRemote('setSnmpLastCollection', device.id)
            driver.next()

        def processClientFinished(result):
            if not result:
                self.log.debug("Client %s finished" % device.id)
            else:
                self.log.error("Client %s finished: %s" % (device.id, result))
            try:
                self.clients.remove(collectorClient)
                self.finished.append(collectorClient)
            except ValueError:
                self.log.warn("client %s not found in active clients",
                              device.id)
            d = drive(self.fillCollectionSlots)
            d.addErrback(self.fillError)
        d = drive(processClient)
        d.addBoth(processClientFinished)



    def fillError(self, reason):
        self.log.error("Unable to fill collection slots: %s" % reason)

    def heartbeat(self, ignored=None):
        ARBITRARY_BEAT = 30
        reactor.callLater(ARBITRARY_BEAT, self.heartbeat)
        if self.options.cycle:
            # as long as we started recently, send a heartbeat
            if not self.start or time.time() - self.start < self.cycletime*3:
                evt = dict(eventClass=Heartbeat,
                           component='zenmodeler',
                           device=self.options.monitor,
                           timeout=3*ARBITRARY_BEAT)
                self.sendEvent(evt)
                self.niceDoggie(self.cycletime)


    def checkStop(self, unused = None):
        "if there's nothing left to do, maybe we should terminate"
        if self.clients: return
        if self.devicegen: return

        if self.start:
            runTime = time.time() - self.start
            self.start = None
            self.log.info("scan time: %0.2f seconds", runTime)
            devices = len(self.finished)
            timedOut = len([c for c in self.finished if c.timedOut])
            self.sendEvents(
                self.rrdStats.gauge('cycleTime', self.cycletime, runTime) +
                self.rrdStats.gauge('devices', self.cycletime, devices) +
                self.rrdStats.gauge('timedOut', self.cycletime, timedOut)
                )
            if not self.options.cycle:
                self.stop()

    def fillCollectionSlots(self, driver):
        """If there are any free collection slots fill them up
        """
        count = len(self.clients)
        while ( count < self.options.parallel and
                self.devicegen and
                not self.slowDown ):
            try:
                device = self.devicegen.next()
                yield self.config().callRemote('getDeviceConfig', [device])
                # just collect one device, and let the timer add more
                devices = driver.next()
                if devices:
                    self.collectDevice(devices[0])
            except StopIteration:
                self.devicegen = None
            break

        update = len(self.clients)
        if update != count and update != 1:
            self.log.info('Running %d clients', update)
        else:
            self.log.debug('Running %d clients', update)
        self.checkStop()


    def buildOptions(self):
        PBDaemon.buildOptions(self)
        self.parser.add_option('--debug',
                dest='debug', action="store_true", default=False,
                help="don't fork threads for processing")
        self.parser.add_option('--nothread',
                dest='nothread', action="store_true", default=True,
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
        # FIXME: cleanup --force option #2660
        self.parser.add_option("-F", "--force",
                    dest="force", action='store_true', default=True,
                    help="force collection of config data (deprecated)")
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


    def timeoutClients(self, unused=None):
        reactor.callLater(1, self.timeoutClients)
        active = []
        for client in self.clients:
            if client.timeout < time.time():
                self.log.warn("client %s timeout", client.hostname)
                self.finished.append(client)
                client.timedOut = True
            else:
                active.append(client)
        self.clients = active
        d = drive(self.fillCollectionSlots)
        d.addCallback(self.checkStop)
        d.addErrback(self.fillError)
                

    def reactorLoop(self):
        reactor.startRunning()
        while reactor.running:
            try:
                while reactor.running:
                    reactor.runUntilCurrent()
                    reactor.doIteration(0)
                    timeout = reactor.timeout()
                    self.slowDown = timeout < 0.01
                    reactor.doIteration(timeout)
            except:
                if reactor.running:
                    self.log.exception("Unexpected error in main loop.")

    def getDeviceList(self):
        if self.options.device:
            self.log.info("collecting for device %s", self.options.device)
            return succeed([self.options.device])
        elif self.options.monitor:
            self.log.info("collecting for monitor %s", self.options.monitor)
            return self.config().callRemote('getDeviceListByMonitor',
                                            self.options.monitor)
        else:
            self.log.info("collecting for path %s", self.options.path)
            return self.config().callRemote('getDeviceListByOrganizer',
                                            self.options.path)
        


    def mainLoop(self, driver):
        if self.options.cycle:
            driveLater(self.cycletime, self.mainLoop)

        if self.clients:
            self.log.error("modeling cycle taking too long")
            return

        self.start = time.time()

        self.log.info("starting collector loop")
        yield self.getDeviceList()
        self.devicegen = iter(driver.next())
        d = drive(self.fillCollectionSlots)
        d.addErrback(self.fillError)
        yield d
        driver.next()
        self.log.debug("Collection slots filled")
        

    def main(self, unused=None):
        self.finished = []
        d = drive(self.mainLoop)
        d.addCallback(self.timeoutClients)
        return d

    def collectSingle(self, device):
        self.finished = []
        self.start = time.time()
        self.devicegen = iter([device])
        d = self.drive(self.fillCollectionSlots)
        d.addCallback(self.timeoutClients)
        d.addErrback(self.fillError)


if __name__ == '__main__':
    dc = ZenModeler()
    dc.processOptions()
    # hook to detect slowdown 
    reactor.run = dc.reactorLoop
    dc.run()
