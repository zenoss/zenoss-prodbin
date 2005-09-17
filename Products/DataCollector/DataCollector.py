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

from twisted.internet import reactor

import Globals

from Acquisition import aq_base

from Products.ZenUtils.Utils import getObjByPath
from Products.ZenUtils.ZCmdBase import ZCmdBase

import CollectorClient
import SshClient
import TelnetClient
from Exceptions import *

defaultProtocol = "ssh"
defaultPort = 22
defaultParallel = 10

class DataCollector(ZCmdBase):
    
    def __init__(self, noopts=0,app=None):
        ZCmdBase.__init__(self,noopts,app)
        self.clients = {}
        if not noopts:
            self.processOptions()            
        self.commandParsers = {} 
        self.deviceMaps = {}
        import CommandParsers
        CommandParsers.initCommandParsers(self)
 


    def addCommandParser(self, commandParser):
        """add an instance of a commandParser"""
        cp = commandParser()
        self.commandParsers[cp.command] = cp


    def collectCommands(self, devices=None):
        if devices: self.devices = devices
        parallel = self.options.parallel
        clients = 0
        while parallel and self.devices:
            client = self.collectDevice(self.devices.pop())
            if client: 
                clients += 1
                parallel -= 1
        if clients: 
            reactor.run()
            for device, maps in self.deviceMaps.items():
                for map in maps:
                    self.applyDataMap(device, map)
        else:
            self.log.warn("no valid clients found")
        

    def collectDevice(self, device):
        try:
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
                self.clients[client] = 1
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
            return client
        except NoServerFound, msg:
            self.log.warn(msg)
        except DataCollectorError:
            self.log.exception("error setting up collector client")


    def getCommands(self, device):
        """go through the parsers for a device and get their commands"""
        aqIgnoreParsers = getattr(device, 'zCommandIgnoreParsers', [])
        aqCollectParsers = getattr(device, 'zCommandCollectParsers', [])
        parsers = []
        for parser in self.commandParsers.values():
            parsername = parser.__class__.__name__
            if (not parser.condition(device, self.log) or 
                parsername in self.options.ignoreParsers or
                parsername in aqIgnoreParsers):
                self.log.debug("skip %s on device %s" % (parsername, device.id))
                continue
            elif (parsername in self.options.collectParsers or
                    parsername in aqCollectParsers):
                self.log.debug("collect %s on device %s" 
                                    % (parsername, device.id))
                parsers.append(parser)
            elif not (self.options.collectParsers or aqCollectParsers):
                self.log.debug("collect %s on device %s" 
                                    % (parsername, device.id))
                parsers.append(parser)
        commands = map(lambda x: x.command, parsers)
        self.log.debug("got commands: %s for %s" % 
            ("' '".join(commands), device.getId()))
        return commands
             
    
    def clientFinished(self, collectorClient):
        """handle the return values from a client and see if we need to stop"""
        self.log.debug("client for %s finished collecting" 
                        % collectorClient.hostname)
        for command, results in collectorClient.getResults():
            device = collectorClient.device
            if not self.commandParsers.has_key(command): continue
            parser = self.commandParsers[command]
            datamap = parser.parse(device, results, self.log)
            #self.applyDataMap(collectorClient.device, datamap)
            if not self.deviceMaps.has_key(device):
                self.deviceMaps[device] = []
            self.deviceMaps[device].append(datamap)
        del self.clients[collectorClient]
        if not self.clients and not self.devices: 
            reactor.stop()
        elif self.devices:
            self.collectDevice(self.devices.pop())


    def applyDataMap(self, device, datamap):
        try:
            device._p_jar.sync()
            from Products.DataCollector.ObjectMap import ObjectMap
            if isinstance(datamap, ObjectMap):
                self.updateObject(device, datamap)
            else:
                self.updateRelationship(device, datamap)
            get_transaction().note(
                "Automated data collection by DataCollector.py")
            get_transaction().commit()
        except:
            get_transaction().abort()
            self.log.exception("ERROR: appling datamap %s to device %s"
                                    % (datamap.getName(), device.getId()))
            
    
        
    def updateRelationship(self, device, relmap):
        """populate the relationship with collected data"""
        rname = relmap.relationshipName
        rel = getattr(device, rname, None)
        if rel:
            relids = rel.objectIdsAll()
            for objectmap in relmap:
                from Products.DataCollector.ObjectMap import ObjectMap
                from Products.ZenModel.ZenModelRM import ZenModelRM
                if isinstance(objectmap, ObjectMap) and objectmap.has_key('id'):
                    if objectmap['id'] in relids:
                        self.updateObject(
                            rel._getOb(objectmap['id']), objectmap)
                        relids.remove(objectmap['id'])
                    else:
                        self.createRelObject(device, objectmap, rname)
                elif isinstance(objectmap, ZenModelRM):
                    self.log.debug("linking object %s to device %s relation %s"
                                        % (objectmap.id, device.id, rname))
                    device.addRelation(rname, objectmap)
                else:
                    self.log.warn("ignoring objectmap no id found")
            for id in relids:
                rel._delObject(id)
        else:
            self.log.warn("No relationship %s found on %s" % 
                                (relmap.relationshipName, device.id))


    def updateObject(self, obj, objectmap):
        """update an object using a objectmap"""
        for attname, value in objectmap.items():
            if attname[0] == '_': continue
            if hasattr(aq_base(obj), attname):
                try:
                    att = getattr(obj, attname)
                    if callable(att):
                        att(value)
                    else:
                        if att != value:
                                setattr(aq_base(obj), attname, value) 
                except:
                    self.log.exception("ERROR: setting attribute %s"
                                            % attname)
                self.log.debug("   Set attribute %s to %s on object %s" 
                                % (attname, value, obj.id))
            else:
                self.log.warn('attribute %s not found on object %s' 
                                % (attname, obj.id))
        obj.index_object() #FIXME do we really need this?
        

    def createRelObject(self, device, objectmap, relationshipName):
        """create an object on a relationship using its objectmap and snmpmap"""
        id = objectmap['id']
        if objectmap.className.find('.') > 0:
            fpath = objectmap.className.split('.')
        else:
            raise ObjectCreationError, \
                "className %s must specify the module and class" % ( 
                                            objectmap.className,)
        constructor = (self._lookupClass(objectmap.className)
                    or getObjByPath(self.app.Control_Panel.Products, fpath))
        if not constructor:
            raise ObjectCreationError, \
                "Can not find factory function for %s" % objectmap.className
        remoteObj = constructor(id)
        if not remoteObj: 
            raise ObjectCreationError, \
                "failed to create object %s in relation %s" % (
                                    id,relationshipName)
                    
        rel = device._getOb(relationshipName, None) 
        if rel:
            rel._setObject(remoteObj.id, remoteObj)
        else:
            raise ObjectCreationError, \
                "No relation %s found on device %s" % (
                            relationshipName, device.id)
        remoteObj = rel._getOb(remoteObj.id)
        self.updateObject(remoteObj, objectmap)
        self.log.debug("   Added object %s to relationship %s" 
                        % (remoteObj.id, relationshipName))
   

    def _lookupClass(self, productName):
        """look in sys.modules for our class"""
        from Products.ZenUtils.Utils import lookupClass
        return lookupClass(productName)


    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--parallel',
                dest='parallel',
                type='int',
                default=defaultParallel,
                help="number of devices to collect from in parallel")
        self.parser.add_option('-i', '--ignore',
                dest='ignoreParsers',
                default=[],
                help="Comma separated list of collection maps to ignore")
        self.parser.add_option('-c', '--collect',
                dest='collectParsers',
                default=[],
                help="Comma separated list of collection maps to use")
        self.parser.add_option('-p', '--path',
                dest='path',
                help="start path for collection ie /Devices")
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
        devices = []
        if (not self.options.path and 
            not self.options.device):
            self.parser.print_help()
            sys.exit(1)
        if self.options.device:
            device = self.findDevice(self.options.device)
            if not device:
                print "unable to locate device %s" % self.options.device
                sys.exit(2)
            devices.append(device)
        if self.options.path:
            devices = self.dataroot.getDmdRoot("Devices")
            droot = devices.getDeviceClass(self.options.path)
            if not droot:
                print "unable to locate device class %s" % self.options.path
                sys.exit(2)
            devices = droot.getSubDevices()
        if self.options.ignoreParsers and self.options.collectParsers:
            print "--ignore and --collect are mutually exclusive"
            sys.exit(1)
        if self.options.ignoreParsers:
            self.options.ignoreParsers = self.options.ignoreParsers.split(',')
        if self.options.collectParsers:
            self.options.collectParsers = self.options.collectParsers.split(',')
        self.devices = devices


def main():
    dc = DataCollector()
    dc.collectCommands()
    

if __name__ == '__main__':
    main()
