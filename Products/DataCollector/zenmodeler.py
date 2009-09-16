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

__doc__= """Discover (aka model) a device and its components.
For instance, find out what Ethernet interfaces and hard disks a server
has available.
This information should change much less frequently than performance metrics.
"""

# IMPORTANT! The import of the pysamba.twisted.reactor module should come before
# any other libraries that might possibly use twisted. This will ensure that
# the proper WmiReactor is installed before anyone else grabs a reference to
# the wrong reactor.
import pysamba.twisted.reactor

import Globals
from Products.ZenWin.WMIClient import WMIClient
from Products.ZenWin.utils import addNTLMv2Option, setNTLMv2Auth
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenUtils.DaemonStats import DaemonStats
from Products.ZenUtils.Driver import drive, driveLater
from Products.ZenUtils.Utils import unused
from Products.ZenEvents.ZenEventClasses import Heartbeat, Error

from PythonClient   import PythonClient
from SshClient      import SshClient
from TelnetClient   import TelnetClient, buildOptions as TCbuildOptions
from SnmpClient     import SnmpClient
from PortscanClient import PortscanClient
                         
from Products.DataCollector import Classifier

from twisted.internet import reactor
from twisted.internet.defer import succeed

import time
import types
import re
import DateTime

import os
import os.path
import sys
import traceback
from random import randint
       
defaultPortScanTimeout = 5
defaultParallel = 1
defaultProtocol = "ssh"
defaultPort = 22

# needed for Twisted's PB (Perspective Broker) to work
from Products.DataCollector import DeviceProxy
from Products.DataCollector import Plugins
unused(DeviceProxy, Plugins)

class ZenModeler(PBDaemon):
    """
    Daemon class to attach to zenhub and pass along
    device configuration information.
    """

    name = 'zenmodeler'
    initialServices = PBDaemon.initialServices + ['ModelerService']
    
    generateEvents = True
    configCycleInterval = 360
    
    classCollectorPlugins = ()

    def __init__(self, single=False ):
        """
        Initalizer

        @param single: collect from a single device?
        @type single: boolean
        """
        PBDaemon.__init__(self)
        # FIXME: cleanup --force option #2660
        self.options.force = True
        self.start = None
        self.rrdStats = DaemonStats()
        self.single = single
        if self.options.device:
            self.single = True
        self.modelerCycleInterval = self.options.cycletime
        self.collage = float( self.options.collage ) / 1440.0
        self.pendingNewClients = False
        self.clients = []
        self.finished = []
        self.devicegen = None
        
        # Delay start for between 10 and 60 minutes when run as a daemon.
        self.started = False
        self.startDelay = 0
        if self.options.daemon:
            if self.options.now:
                self.log.debug("Run as a daemon, starting immediately.")
            else:
                # self.startDelay = randint(10, 60) * 60
                self.startDelay = randint(10, 60) * 1
                self.log.info("Run as a daemon, waiting %s seconds to start." %
                              self.startDelay)
        else:
            self.log.debug("Run in foreground, starting immediately.")


    def reportError(self, error):
        """
        Log errors that have occurred

        @param error: error message
        @type error: string
        """
        self.log.error("Error occured: %s", error)


    def connected(self):
        """
        Called after connected to the zenhub service
        """
        d = self.configure()
        d.addCallback(self.heartbeat)
        d.addErrback(self.reportError)
    

    def configure(self):
        """
        Get our configuration from zenhub
        """
        # add in the code to fetch cycle time, etc.
        def inner(driver):
            """
            Generator function to gather our configuration

            @param driver: driver object
            @type driver: driver object
            """
            self.log.debug('fetching monitor properties')
            yield self.config().callRemote('propertyItems')
            items = dict(driver.next())
            if self.options.cycletime == 0:
                self.modelerCycleInterval = items.get('modelerCycleInterval',
                                                      self.modelerCycleInterval)
            self.configCycleInterval = items.get('configCycleInterval',
                                                 self.configCycleInterval)
            reactor.callLater(self.configCycleInterval * 60, self.configure)

            self.log.debug("Getting threshold classes...")
            yield self.config().callRemote('getThresholdClasses')
            self.remote_updateThresholdClasses(driver.next())

            self.log.debug("Fetching default RRDCreateCommand...")
            yield self.config().callRemote('getDefaultRRDCreateCommand')
            createCommand = driver.next()

            self.log.debug("Getting collector thresholds...")
            yield self.config().callRemote('getCollectorThresholds')
            self.rrdStats.config(self.options.monitor,
                                 self.name,
                                 driver.next(),
                                 createCommand)

            self.log.debug("Getting collector plugins for each DeviceClass")
            yield self.config().callRemote('getClassCollectorPlugins')
            self.classCollectorPlugins = driver.next()
                                             
        return drive(inner)


    def config(self):
        """
        Get the ModelerService
        """
        return self.services.get('ModelerService', FakeRemote())


    def selectPlugins(self, device, transport):
        """
        Build a list of active plugins for a device, based on:

        * the --collect command-line option which is a regex
        * the --ignore command-line option which is a regex
        * transport which is a string describing the type of plugin

        @param device: device to collect against
        @type device: string
        @param transport: python, ssh, snmp, telnet, cmd
        @type transport: string
        @return: results of the plugin
        @type: string
        @todo: determine if an event for the collector AND the device should be sent
        """
        plugins = []
        valid_loaders = []
        for loader in device.plugins:
            try:
                plugin= loader.create()
                self.log.debug( "Loaded plugin %s" % plugin.name() )
                plugins.append( plugin )
                valid_loaders.append( loader )

            except (SystemExit, KeyboardInterrupt), ex:
                self.log.info( "Interrupted by external signal (%s)" % str(ex) )
                raise

            except Plugins.PluginImportError, import_error:
                import socket
                component, _ = os.path.splitext( os.path.basename( sys.argv[0] ) )
                collector_host= socket.gethostname()
                # NB: an import errror affects all devices,
                #     so report the issue against the collector
                # TOOD: determine if an event for the collector AND the device should be sent
                evt= { "eventClass":"/Status/Update", "component":component,
                      "agent":collector_host, "device":collector_host,
                      "severity":Error }

                info= "Problem loading plugin %s" % import_error.plugin
                self.log.error( info )
                evt[ 'summary' ]= info

                info= import_error.traceback
                self.log.error( info )
                evt[ 'message' ]= info

                info= ("Due to import errors, removing the %s plugin"
                       " from this collection cycle.") % import_error.plugin
                self.log.error( info )
                evt[ 'message' ] += "%s\n" % info
                self.sendEvent( evt )

        # Make sure that we don't generate messages for bad loaders again
        # NB: doesn't update the device's zProperties
        if len( device.plugins ) != len( valid_loaders ):
            device.plugins= valid_loaders

        # Create functions to search for what plugins we will and
        # won't supply to the device
        collectTest = lambda x: False
        ignoreTest = lambda x: False
        if self.options.collectPlugins:
            collectTest = re.compile(self.options.collectPlugins).search
        elif self.options.ignorePlugins:
            ignoreTest = re.compile(self.options.ignorePlugins).search

        result = []
        for plugin in plugins:
            if plugin.transport != transport:
                continue
            name = plugin.name()
            if ignoreTest(name):
                self.log.debug("Ignoring %s on %s because of --ignore flag",
                               name, device.id)
            elif collectTest(name):
                self.log.debug("Using %s on %s because of --collect flag",
                               name, device.id)
                result.append(plugin)
            elif not self.options.collectPlugins:
                self.log.debug("Using %s on %s", name, device.id)
                result.append(plugin)
        return result



    def collectDevice(self, device):
        """
        Collect data from a single device.

        @param device: device to collect against
        @type device: string
        """
        clientTimeout = getattr(device, 'zCollectorClientTimeout', 180)
        ip = device.manageIp
        timeout = clientTimeout + time.time()
        self.wmiCollect(device, ip, timeout)
        self.pythonCollect(device, ip, timeout)
        self.cmdCollect(device, ip, timeout) 
        self.snmpCollect(device, ip, timeout)
        self.portscanCollect(device, ip, timeout)



    def wmiCollect(self, device, ip, timeout):
        """
        Start the Windows Management Instrumentation (WMI) collector

        @param device: device to collect against
        @type device: string
        @param ip: IP address of device to collect against
        @type ip: string
        @param timeout: timeout before failing the connection
        @type timeout: integer
        """
        if self.options.nowmi:
            return

        client = None
        try:
            plugins = self.selectPlugins(device, 'wmi')
            if not plugins:
                self.log.info("No WMI plugins found for %s" % device.id)
                return
            if self.checkCollection(device):
                self.log.info('WMI collector method for device %s' % device.id)
                self.log.info("plugins: %s",
                        ", ".join(map(lambda p: p.name(), plugins)))
                client = WMIClient(device, self, plugins)
            if not client or not plugins:
                self.log.warn("WMI collector creation failed")
                return
        except (SystemExit, KeyboardInterrupt):
            raise
        except Exception:
            self.log.exception("Error opening WMI collector")
        self.addClient(client, timeout, 'WMI', device.id)



    def pythonCollect(self, device, ip, timeout):
        """
        Start local Python collection client.

        @param device: device to collect against
        @type device: string
        @param ip: IP address of device to collect against
        @type ip: string
        @param timeout: timeout before failing the connection
        @type timeout: integer
        """
        client = None
        try:
            plugins = self.selectPlugins(device, "python")
            if not plugins:
                self.log.info("No Python plugins found for %s" % device.id)
                return
            if self.checkCollection(device):
                self.log.info('Python collection device %s' % device.id)
                self.log.info("plugins: %s",
                        ", ".join(map(lambda p: p.name(), plugins)))
                client = PythonClient(device, self, plugins)
            if not client or not plugins:
                self.log.warn("Python client creation failed")
                return
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("Error opening pythonclient")
        self.addClient(client, timeout, 'python', device.id)


    def cmdCollect(self, device, ip, timeout):
        """
        Start shell command collection client.

        @param device: device to collect against
        @type device: string
        @param ip: IP address of device to collect against
        @type ip: string
        @param timeout: timeout before failing the connection
        @type timeout: integer
        """
        client = None
        clientType = 'snmp' # default to SNMP if we can't figure out a protocol

        hostname = device.id
        try:
            plugins = self.selectPlugins(device,"command")
            if not plugins:
                self.log.info("No command plugins found for %s" % hostname)
                return

            protocol = getattr(device, 'zCommandProtocol', defaultProtocol)
            commandPort = getattr(device, 'zCommandPort', defaultPort)

            if protocol == "ssh":
                client = SshClient(hostname, ip, commandPort,
                                   options=self.options,
                                   plugins=plugins, device=device,
                                   datacollector=self, isLoseConnection=True)
                clientType = 'ssh'
                self.log.info('Using SSH collection method for device %s'
                              % hostname)

            elif protocol == 'telnet':
                if commandPort == 22: commandPort = 23 #set default telnet
                client = TelnetClient(hostname, ip, commandPort,
                                      options=self.options,
                                      plugins=plugins, device=device,
                                      datacollector=self)
                clientType = 'telnet'
                self.log.info('Using telnet collection method for device %s'
                              % hostname)

            else:
                info = ("Unknown protocol %s for device %s -- "
                        "defaulting to %s collection method" %
                        (protocol, hostname, clientType ))
                self.log.warn( info )
                import socket
                component, _ = os.path.splitext( os.path.basename( sys.argv[0] ) )
                collector_host= socket.gethostname()
                evt= { "eventClass":"/Status/Update", "agent":collector_host,
                      "device":hostname, "severity":Error }
                evt[ 'summary' ]= info
                self.sendEvent( evt )
                return

            if not client:
                self.log.warn("Shell command collector creation failed")
            else:
                self.log.info("plugins: %s",
                    ", ".join(map(lambda p: p.name(), plugins)))
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("Error opening command collector")
        self.addClient(client, timeout, clientType, device.id)



    def snmpCollect(self, device, ip, timeout):
        """
        Start SNMP collection client.

        @param device: device to collect against
        @type device: string
        @param ip: IP address of device to collect against
        @type ip: string
        @param timeout: timeout before failing the connection
        @type timeout: integer
        """
        client = None
        try:
            hostname = device.id
            if getattr( device, "zSnmpMonitorIgnore", True ):
                self.log.info("SNMP monitoring off for %s" % hostname)
                return

            if not ip:
                self.log.info("No manage IP for %s" % hostname)
                return

            plugins = []
            plugins = self.selectPlugins(device,"snmp")
            if not plugins:
                self.log.info("No SNMP plugins found for %s" % hostname)
                return

            if self.checkCollection(device):
                self.log.info('SNMP collection device %s' % hostname)
                self.log.info("plugins: %s",
                              ", ".join(map(lambda p: p.name(), plugins)))
                client = SnmpClient(device.id, ip, self.options,
                                    device, self, plugins)
            if not client or not plugins:
                self.log.warn("SNMP collector creation failed")
                return
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("Error opening the SNMP collector")
        self.addClient(client, timeout, 'SNMP', device.id)


######## need to make async test for snmp work at some point -EAD #########
    # def checkSnmpConnection(self, device):
    #     """
    #     Check to see if our current community string is still valid
    #     
    #     @param device: the device against which we will check
    #     @type device: a Device instance
    #     @return: result is None or a tuple containing 
    #             (community, port, version, snmp name)
    #     @rtype: deferred: Twisted deferred
    #     """
    #     from pynetsnmp.twistedsnmp import AgentProxy
    # 
    #     def inner(driver):
    #         self.log.debug("Checking SNMP community %s on %s",
    #                         device.zSnmpCommunity, device.id)
    # 
    #         oid = ".1.3.6.1.2.1.1.5.0"
    #         proxy = AgentProxy(device.id,
    #                            device.zSnmpPort,
    #                            timeout=device.zSnmpTimeout,
    #                            community=device.zSnmpCommunity,
    #                            snmpVersion=device.zSnmpVer,
    #                            tries=2)
    #         proxy.open()
    #         yield proxy.get([oid])
    #         devname = driver.next().values()[0]
    #         if devname: 
    #             yield succeed(True)
    #         yield succeed(False)  
    # 
    #     return drive(inner)


    def addClient(self, device, timeout, clientType, name):
        """
        If device is not None, schedule the device to be collected.
        Otherwise log an error.

        @param device: device to collect against
        @type device: string
        @param timeout: timeout before failing the connection
        @type timeout: integer
        @param clientType: description of the plugin type
        @type clientType: string
        @param name: plugin name
        @type name: string
        """
        if device:
            device.timeout = timeout
            device.timedOut = False
            self.clients.append(device)
            device.run()
        else:
            self.log.warn('Unable to create a %s collector for %s',
                          clientType, name)


    # XXX double-check this, once the implementation is in place
    def portscanCollect(self, device, ip, timeout):
        """
        Start portscan collection client.

        @param device: device to collect against
        @type device: string
        @param ip: IP address of device to collect against
        @type ip: string
        @param timeout: timeout before failing the connection
        @type timeout: integer
        """
        client = None
        try:
            hostname = device.id
            plugins = self.selectPlugins(device, "portscan")
            if not plugins:
                self.log.info("No portscan plugins found for %s" % hostname)
                return
            if self.checkCollection(device):
                self.log.info('Portscan collector method for device %s'
                              % hostname)
                self.log.info("plugins: %s",
                    ", ".join(map(lambda p: p.name(), plugins)))
                client = PortscanClient(device.id, ip, self.options,
                                        device, self, plugins)
            if not client or not plugins:
                self.log.warn("Portscan collector creation failed")
                return
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("Error opening portscan collector")
        self.addClient(client, timeout, 'portscan', device.id)


    def checkCollection(self, device):
        """
        See how old the data is that we've collected

        @param device: device to collect against
        @type device: string
        @return: is the SNMP status number > 0 and is the last collection time + collage older than now?
        @type: boolean
        """
        age = device.getSnmpLastCollection() + self.collage
        if device.getSnmpStatusNumber() > 0 and age >= DateTime.DateTime():
            self.log.info("Skipped collection of %s" % device.id)
            return False
        return True


    def clientFinished(self, collectorClient):
        """
        Callback that processes the return values from a device.
        Python iterable.

        @param collectorClient: collector instance
        @type collectorClient: collector class
        @return: Twisted deferred object
        @type: Twisted deferred object
        """
        device = collectorClient.device
        self.log.debug("Client for %s finished collecting", device.id)
        def processClient(driver):
            try:
                pluginStats = {}
                self.log.debug("Processing data for device %s", device.id)
                devchanged = False
                maps = []
                for plugin, results in collectorClient.getResults():
                    if plugin is None: continue
                    self.log.debug("Processing plugin %s on device %s ...",
                                   plugin.name(), device.id)
                    if not results:
                        self.log.warn("The plugin %s returned no results.",
                                      plugin.name())
                        continue

                    datamaps = []
                    try:
                        results = plugin.preprocess(results, self.log)
                        if results:
                            datamaps = plugin.process(device, results, self.log)
                        if datamaps:
                            pluginStats.setdefault(plugin.name(), plugin.weight)

                    except (SystemExit, KeyboardInterrupt), ex:
                        self.log.info( "Plugin %s terminated due to external"
                                      " signal (%s)" % (plugin.name(), str(ex) )
                                      )
                        continue

                    except Exception, ex:
                        # NB: don't discard the plugin, as it might be a
                        #     temporary issue
                        #     Also, report it against the device, rather than at
                        #     a collector as it might be just for this device.
                        import socket
                        component= os.path.splitext(
                            os.path.basename( sys.argv[0] )
                            )[0]
                        collector_host= socket.gethostname()
                        evt= { "eventClass":"/Status/Update",
                              "agent":collector_host, "device":device.id,
                              "severity":Error }

                        info= "Problem while executing plugin %s" %plugin.name()
                        self.log.error( info )
                        evt[ 'summary' ]= info

                        info= traceback.format_exc()
                        self.log.error( info )
                        evt[ 'message' ]= info
                        self.sendEvent( evt )
                        continue

                    # allow multiple maps to be returned from one plugin
                    if type(datamaps) not in (types.ListType, types.TupleType):
                        datamaps = [datamaps,]
                    if datamaps:
                        maps += [m for m in datamaps if m]
                if maps:                             
                    deviceClass = Classifier.classifyDevice(pluginStats,
                                                self.classCollectorPlugins)
                    yield self.config().callRemote(
                                                'applyDataMaps', device.id,
                                                maps, deviceClass)
                    if driver.next():
                        devchanged = True
                if devchanged:
                    self.log.info("Changes in configuration applied")
                else:
                    self.log.info("No change in configuration detected")
                yield self.config().callRemote('setSnmpLastCollection',
                                               device.id)
                driver.next()
            except Exception, ex:
                self.log.exception(ex)
                raise
 
        def processClientFinished(result):
            """
            Called after the client collection finishes

            @param result: object (unused)
            @type result: object
            """
            if not result:
                self.log.debug("Client %s finished" % device.id)
            else:
                self.log.error("Client %s finished with message: %s" %
                               (device.id, result))
            try:
                self.clients.remove(collectorClient)
                self.finished.append(collectorClient)
            except ValueError:
                self.log.debug("Client %s not found in in the list"
                              " of active clients",
                              device.id)
            d = drive(self.fillCollectionSlots)
            d.addErrback(self.fillError)

        d = drive(processClient)
        d.addBoth(processClientFinished)



    def fillError(self, reason):
        """
        Twisted errback routine to log an error when
        unable to collect some data

        @param reason: error message
        @type reason: string
        """
        self.log.error("Unable to fill collection slots: %s" % reason)


    def cycleTime(self):
        """
        Return our cycle time (in minutes)

        @return: cycle time
        @rtype: integer
        """
        return self.modelerCycleInterval * 60


    def heartbeat(self, ignored=None):
        """
        Twisted keep-alive mechanism to ensure that
        we're still connected to zenhub

        @param ignored: object (unused)
        @type ignored: object
        """
        ARBITRARY_BEAT = 30
        reactor.callLater(ARBITRARY_BEAT, self.heartbeat)
        if self.options.cycle:
            evt = dict(eventClass=Heartbeat,
                       component='zenmodeler',
                       device=self.options.monitor,
                       timeout=3*ARBITRARY_BEAT)
            self.sendEvent(evt)
            self.niceDoggie(self.cycleTime())
        
        # We start modeling from here to accomodate the startup delay.
        if not self.started:
            self.started = True
            reactor.callLater(self.startDelay, self.main)


    def checkStop(self, unused = None):
        """
        Check to see if there's anything to do.
        If there isn't, report our statistics and exit.

        @param unused: unused (unused)
        @type unused: string
        """
        if self.clients: return
        if self.devicegen: return

        if self.start:
            runTime = time.time() - self.start
            self.start = None
            self.log.info("Scan time: %0.2f seconds", runTime)
            devices = len(self.finished)
            timedOut = len([c for c in self.finished if c.timedOut])
            self.sendEvents(
                self.rrdStats.gauge('cycleTime', self.cycleTime(), runTime) +
                self.rrdStats.gauge('devices', self.cycleTime(), devices) +
                self.rrdStats.gauge('timedOut', self.cycleTime(), timedOut)
                )
            if not self.options.cycle:
                self.stop()
            self.finished = []


    def fillCollectionSlots(self, driver):
        """
        An iterator which either returns a device to collect or
        calls checkStop()

        @param driver: driver object
        @type driver: driver object
        """
        count = len(self.clients)
        while count < self.options.parallel and self.devicegen \
            and not self.pendingNewClients:
            
            self.pendingNewClients = True
            try:
                device = self.devicegen.next()
                yield self.config().callRemote('getDeviceConfig', [device])
                # just collect one device, and let the timer add more
                devices = driver.next()
                if devices:
                    self.collectDevice(devices[0])
            except StopIteration:
                self.devicegen = None
            
            self.pendingNewClients = False
            break

        update = len(self.clients)
        if update != count and update != 1:
            self.log.info('Running %d clients', update)
        else:
            self.log.debug('Running %d clients', update)
        self.checkStop()


    def buildOptions(self):
        """
        Build our list of command-line options
        """
        PBDaemon.buildOptions(self)
        self.parser.add_option('--debug',
                dest='debug', action="store_true", default=False,
                help="Don't fork threads for processing")
        self.parser.add_option('--nowmi',
                dest='nowmi', action="store_true", default=False,
                help="Do not execute WMI plugins")
        self.parser.add_option('--parallel', dest='parallel',
                type='int', default=defaultParallel,
                help="Number of devices to collect from in parallel")
        self.parser.add_option('--cycletime',
                dest='cycletime',default=720,type='int',
                help="Run collection every x minutes")
        self.parser.add_option('--ignore',
                dest='ignorePlugins',default="",
                help="Modeler plugins to ignore. Takes a regular expression")
        self.parser.add_option('--collect',
                dest='collectPlugins',default="",
                help="Modeler plugins to use. Takes a regular expression")
        self.parser.add_option('-p', '--path', dest='path',
                help="Start class path for collection ie /NetworkDevices")
        self.parser.add_option('-d', '--device', dest='device', 
                help="Fully qualified device name ie www.confmon.com")
        self.parser.add_option('-a', '--collage',
                dest='collage', default=0, type='float',
                help="Do not collect from devices whose collect date " +
                        "is within this many minutes")
        self.parser.add_option('--writetries',
                dest='writetries',default=2,type='int',
                help="Number of times to try to write if a "
                     "read conflict is found")
        # FIXME: cleanup --force option #2660
        self.parser.add_option("-F", "--force",
                    dest="force", action='store_true', default=True,
                    help="Force collection of config data (deprecated)")
        self.parser.add_option('--portscantimeout', dest='portscantimeout',
                type='int', default=defaultPortScanTimeout,
                help="Time to wait for connection failures when port scanning")
        self.parser.add_option('--now',
                dest='now', action="store_true", default=False,
                help="Start daemon now, do not sleep before starting")
        TCbuildOptions(self.parser, self.usage)
        addNTLMv2Option(self.parser)



    def processOptions(self):
        """
        Check what the user gave us vs what we'll accept
        for command-line options
        """
        if not self.options.path and not self.options.device:
            self.options.path = "/Devices"
        if self.options.ignorePlugins and self.options.collectPlugins:
            raise SystemExit( "Only one of --ignore or --collect"
                             " can be used at a time")
        setNTLMv2Auth(self.options)

    def _timeoutClients(self):
        """
        The guts of the timeoutClients method (minus the twisted reactor
        stuff). Breaking this part out as a separate method facilitates unit
        testing.
        """
        active = []
        for client in self.clients:
            if client.timeout < time.time():
                self.log.warn("Client %s timeout", client.hostname)
                self.finished.append(client)
                client.timedOut = True
                client.stop()
            else:
                active.append(client)
        self.clients = active
        


    def timeoutClients(self, unused=None):
        """
        Check to see which clients have timed out and which ones haven't.
        Stop processing anything that's timed out.

        @param unused: unused (unused)
        @type unused: string
        """
        reactor.callLater(1, self.timeoutClients)
        self._timeoutClients()
        d = drive(self.fillCollectionSlots)
        d.addCallback(self.checkStop)
        d.addErrback(self.fillError)



    def reactorLoop(self):
        """
        Twisted main loop
        """
        reactor.startRunning()
        while reactor.running:
            try:
                while reactor.running:
                    reactor.runUntilCurrent()
                    timeout = reactor.timeout()
                    reactor.doIteration(timeout)
            except:
                if reactor.running:
                    self.log.exception("Unexpected error in main loop.")



    def getDeviceList(self):
        """
        Get the list of devices for which we are collecting:
        * if -d devicename was used, use the devicename
        * if a class path flag was supplied, gather the devices
          along that organizer
        * otherwise get all of the devices associated with our collector

        @return: list of devices
        @rtype: list
        """
        if self.options.device:
            self.log.info("Collecting for device %s", self.options.device)
            return succeed([self.options.device])

        self.log.info("Collecting for path %s", self.options.path)
        return self.config().callRemote('getDeviceListByOrganizer',
                                        self.options.path,
                                        self.options.monitor)


    def mainLoop(self, driver):
        """
        Main collection loop, a Python iterable

        @param driver: driver object
        @type driver: driver object
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        if self.options.cycle:
            driveLater(self.cycleTime(), self.mainLoop)

        if self.clients:
            self.log.error("Modeling cycle taking too long")
            return

        self.start = time.time()

        self.log.debug("Starting collector loop...")
        yield self.getDeviceList()
        self.devicegen = iter(driver.next())
        d = drive(self.fillCollectionSlots)
        d.addErrback(self.fillError)
        yield d
        driver.next()
        self.log.debug("Collection slots filled")



    def main(self, unused=None):
        """
        Wrapper around the mainLoop

        @param unused: unused (unused)
        @type unused: string
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        self.finished = []
        d = drive(self.mainLoop)
        d.addCallback(self.timeoutClients)
        return d



    def remote_deleteDevice(self, device):
        """
        Stub function

        @param device: device name (unused)
        @type device: string
        @todo: implement
        """
        # we fetch the device list before every scan
        self.log.debug("Asynch deleteDevice %s" % device)


if __name__ == '__main__':
    dc = ZenModeler()
    dc.processOptions()
    reactor.run = dc.reactorLoop
    dc.run()
