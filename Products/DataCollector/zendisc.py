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

__doc__ = """zendisc
Scan networks and routes looking for devices to add to the ZODB
"""

import socket

import Globals

from Products.DataCollector.zenmodeler import ZenModeler
from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.Driver import drive
from Products.ZenUtils.IpUtil import asyncNameLookup
from Products.ZenUtils.IpUtil import isip
from Products.ZenUtils.NJobs import NJobs
from Products.ZenModel.Exceptions import NoIPAddress
from Products.ZenEvents.ZenEventClasses import Status_Snmp
from Products.ZenEvents.Event import Info
from Products.ZenStatus.AsyncPing import Ping
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenHub.services  import DiscoverService, ModelerService
unused(DiscoverService, ModelerService) # for pb


from twisted.internet.defer import succeed
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.names.error import DNSNameError


class ZenDisc(ZenModeler):
    """
    Scan networks and routes looking for devices to add to the ZODB
    """

    initialServices = PBDaemon.initialServices + ['DiscoverService']
    name = 'zendisc'
    scanned = 0

    def __init__(self, single=True ):
        """
        Initalizer

        @param single: collect from a single device?
        @type single: boolean
        """
        ZenModeler.__init__(self, single )
        if not self.options.useFileDescriptor:
            self.openPrivilegedPort('--ping')
        self.discovered = []
        sock = None
        if self.options.useFileDescriptor:
            sock = int(self.options.useFileDescriptor)
        self.ping = Ping(self.options.tries,
                         self.options.timeout,
                         sock=sock)

        
    def config(self):
        """
        Get the DiscoverService

        @return: a DiscoverService from zenhub
        @rtype: function
        """
        return self.services.get('DiscoverService', FakeRemote())
    

    def discoverIps(self, nets):
        """
        Ping all ips, create entries in the network if necessary.

        @param nets: list of networks to discover
        @type nets: list
        @return: successful result is a list of IPs that were added
        @rtype: Twisted deferred
        """
        def inner(driver):
            """
            Twisted driver class to iterate through devices

            @param driver: Zenoss driver
            @type driver: Zenoss driver
            @return: successful result is a list of IPs that were added
            @rtype: Twisted deferred
            """
            ips = []
            goodCount = 0
            ips = []
            # it would be nice to interleave ping/discover
            for net in nets:
                if self.options.subnets and len(net.children()) > 0:
                    continue
                if not getattr(net, "zAutoDiscover", False): 
                    self.log.info("Skipping network %s because zAutoDiscover is False"
                                  % net.getNetworkName())
                    continue
                self.log.info("Discover network '%s'", net.getNetworkName())
                yield NJobs(self.options.chunkSize,
                            self.ping.ping,
                            net.fullIpList()).start()
                results = driver.next()
                goodips = [
                    v.ipaddr for v in results if not isinstance(v, Failure)]
                badips = [
                    v.value.ipaddr for v in results if isinstance(v, Failure)]
                goodCount += len(goodips)
                self.log.debug("Got %d good IPs and %d bad IPs",
                               len(goodips), len(badips))
                yield self.config().callRemote('pingStatus',
                                               net,
                                               goodips,
                                               badips,
                                               self.options.resetPtr,
                                               self.options.addInactive)
                ips += driver.next()
                self.log.info("Discovered %s active ips", goodCount)
            # make sure this is the return result for the driver
            yield succeed(ips)
            driver.next()

        d = drive(inner)
        return d
       

    def discoverRouters(self, rootdev, seenips=None):
        """
        Discover all default routers based on DMD configuration.

        @param rootdev: device root in DMD
        @type rootdev: device class
        @param seenips: list of IP addresses
        @type seenips: list of strings
        @return: Twisted/Zenoss Python iterable
        @rtype: Python iterable
        """
        if not seenips:
            seenips = []

        def inner(driver):
            """
            Twisted driver class to iterate through devices

            @param driver: Zenoss driver
            @type driver: Zenoss driver
            @return: successful result is a list of IPs that were added
            @rtype: Twisted deferred
            """
            yield self.config().callRemote('followNextHopIps', rootdev.id)
            for ip in driver.next():
                if ip in seenips:
                    continue
                self.log.info("device '%s' next hop '%s'", rootdev.id, ip)
                seenips.append(ip)
                yield self.discoverDevice(ip, devicepath="/Network/Router")
                router = driver.next()
                if not router:
                    continue
                yield self.discoverRouters(router, seenips)
                driver.next()

        return drive(inner)
            

    def sendDiscoveredEvent(self, ip, dev=None, sev=2):
        """
        Send a 'device discovered' event through zenhub

        @param ip: IP addresses
        @type ip: strings
        @param dev: remote device name
        @type dev: device object
        @param sev: severity
        @type sev: integer
        """
        devname = comp = ip
        if dev: 
            devname = dev.id
        msg = "'Discovered device name '%s' for ip '%s'" % (devname, ip)
        evt = dict(device=devname,ipAddress=ip,eventKey=ip,
                   component=comp,eventClass=Status_Snmp,
                   summary=msg, severity=sev,
                   agent="Discover")
        self.sendEvent(evt)
    
    
    def discoverDevices(self,
                        ips, 
                        devicepath="/Discovered",
                        prodState=1000):
        """
        Discover devices by active ips that are not associated with a device.

        @param ips: list of IP addresses
        @type ips: list of strings
        @param devicepath: where in the DMD to put any discovered devices
        @type devicepath: string
        @param prodState: production state (see Admin Guide for a description)
        @type prodState: integer
        @return: Twisted/Zenoss Python iterable
        @rtype: Python iterable
        """
        def discoverDevice(ip):
            """
            Discover a particular device
            NB: Wrapper around self.discoverDevice()

            @param ip: IP address
            @type ip: string
            @return: Twisted/Zenoss Python iterable
            @rtype: Python iterable
            """
            return self.discoverDevice(ip, devicepath, prodState)

        return NJobs(self.options.parallel, discoverDevice, ips).start()


    def findRemoteDeviceInfo(self, ip, devicePath):
        """
        Scan a device for ways of naming it: PTR DNS record or a SNMP name

        @param ip: IP address
        @type ip: string
        @param devicePath: where in the DMD to put any discovered devices
        @type devicePath: string
        @return: result is None or a tuple containing (community, port, version, snmp name)
        @rtype: deferred: Twisted deferred
        """
        from pynetsnmp.twistedsnmp import AgentProxy

        def inner(driver):
            """
            Twisted driver class to iterate through devices

            @param driver: Zenoss driver
            @type driver: Zenoss driver
            @return: successful result is a list of IPs that were added
            @rtype: Twisted deferred
            """
            self.log.debug("Doing SNMP lookup on device %s", ip)
            yield self.config().callRemote('getSnmpConfig', devicePath)
            communities, port, version, timeout, retries = driver.next()

            # Override with the stuff passed in
            if self.options.zSnmpVer: version = self.options.zSnmpVer
            if self.options.zSnmpPort: port = self.options.zSnmpPort
            if self.options.zSnmpCommunity: 
                communities = (self.options.zSnmpCommunity,)+tuple(communities)

            versions = ("v2c", "v1")
            if '1' in version:
                versions = list(versions)
                versions.reverse()
            oid = ".1.3.6.1.2.1.1.5.0"
            goodcommunity = ""
            goodversion = ""
            devname = ""
            for version in versions:
                for community in communities:
                    proxy = AgentProxy(ip,
                                       port,
                                       timeout=timeout,
                                       community=community,
                                       snmpVersion=version,
                                       tries=retries - 1)
                    proxy.open()
                    try:
                        yield proxy.get([oid])
                        devname = driver.next().values()[0]
                        goodcommunity = community
                        goodversion = version
                        break
                    except:
                        pass
                    proxy.close()
                if goodcommunity:
                    yield succeed((goodcommunity, port, goodversion, devname))
                    break
            else:
                yield succeed(None)
            driver.next()
            self.log.debug("Finished SNMP lookup on device %s", ip)

        return drive(inner)


    def discoverDevice(self, ip, devicepath="/Discovered", prodState=1000):
        """
        Discover a device based on its IP address.

        @param ip: IP address
        @type ip: string
        @param devicepath: where in the DMD to put any discovered devices
        @type devicepath: string
        @param prodState: production state (see Admin Guide for a description)
        @type prodState: integer
        @return: Twisted/Zenoss Python iterable
        @rtype: Python iterable
        """
        self.scanned += 1
        if self.options.maxdevices:
            if self.scanned >= self.options.maxdevices:
                self.log.info("Limit of %d devices reached" %
                              self.options.maxdevices)
                return succeed(None)

        def inner(driver):
            """
            Twisted driver class to iterate through devices

            @param driver: Zenoss driver
            @type driver: Zenoss driver
            @return: successful result is a list of IPs that were added
            @rtype: Twisted deferred
            @todo: modularize this function (130+ lines is ridiculous)
            """
            try:
                kw = dict(deviceName=ip,
                          discoverProto=None,
                          devicePath=devicepath,
                          performanceMonitor=self.options.monitor)

                snmpDeviceInfo = None
                # if we are using SNMP, lookup the device SNMP info and use the
                # name defined there for deviceName
                if not self.options.nosnmp:
                    self.log.debug("Scanning device with address %s", ip)
                    yield self.findRemoteDeviceInfo(ip, devicepath)
                    snmpDeviceInfo = driver.next()
                    if snmpDeviceInfo:
                        keys = ('zSnmpCommunity', 'zSnmpPort', 'zSnmpVer', 
                                'deviceName')
                        snmpDeviceInfo = dict(zip(keys, snmpDeviceInfo))
                        for k, v in snmpDeviceInfo.iteritems():
                            # Only override if not empty
                            if v: kw[k] = v
                    # if we are using SNMP, did not find any snmp info,
                    # and we are in strict discovery mode, do not
                    # create a device
                    elif self.options.zSnmpStrictDiscovery:
                        self.log.info('zSnmpStrictDiscovery is True.  ' +
                                      'Not creating device for %s.'
                                      % ip )
                        return
                        
                # RULES FOR DEVICE NAMING:
                # 1. If zPreferSnmpNaming is true: 
                #        If snmp name is returned, use snmp name. Otherwise, 
                #        use the passed device name.  If no device name was passed,
                #        do a dns lookup on the ip.
                # 2. If zPreferSnmpNaming is false: 
                #        If we are discovering a single device and a name is 
                #        passed in instead of an IP, use the passed-in name.
                #        Otherwise, do a dns lookup on the ip. 
                #import pydevd;pydevd.settrace()
                if self.options.zPreferSnmpNaming and \
                   not isip( kw['deviceName'] ):
                    # In this case, we want to keep kw['deviceName'] as-is,
                    # because it is what we got from snmp
                    pass
                elif self.options.device and not isip(self.options.device):
                    kw['deviceName'] = self.options.device
                else:
                    # An IP was passed in so we do a reverse lookup on it to get
                    # deviceName
                    yield asyncNameLookup(ip)
                    try:
                        kw.update(dict(deviceName=driver.next()))
                    except Exception, ex:
                        self.log.debug("Failed to lookup %s (%s)" % (ip, ex))

                # if there is no SNMP lookup or the lookup failed set the SNMP
                # info that was passed in on the command line so that it will
                # flow through to createDevice. 
                if not snmpDeviceInfo or self.options.nosnmp: 
                    """use the port set via commandline incase 
                    findRemoteDeviceInfo did not return data; this should
                    make sure the device is created with correct snmp 
                    options and zenmodeler runs with correct options"""   
                    if self.options.zSnmpPort: 
                        kw.update(dict(zSnmpPort=self.options.zSnmpPort))
                    if self.options.zSnmpVer: 
                        kw.update(dict(zSnmpVer=self.options.zSnmpVer))
                    if self.options.zSnmpCommunity: 
                        kw.update(dict(zSnmpCommunity=
                                       self.options.zSnmpCommunity))


                # If it's discovering a particular device, 
                # ignore zAutoDiscover limitations
                forceDiscovery = bool(self.options.device) 

                # now create the device by calling zenhub
                yield self.config().callRemote('createDevice', ip, 
                                   force=forceDiscovery, **kw)

                result = driver.next()
                if isinstance(result, Failure):
                    raise ZentinelException(result.value)
                dev, created = result

                # if no device came back from createDevice we assume that it
                # was told to not auto-discover the device.  This seems very
                # dubious to me! -EAD
                if not dev:
                    self.log.info("IP '%s' on no auto-discover, skipping",ip)
                    return
                else:
                    # A device came back and it already existed.
                    if not created:
                        # if we shouldn't remodel skip the device by returning
                        # at the end of this block
                        if not self.options.remodel:
                            self.log.info("Found IP '%s' on device '%s';"
                                          " skipping discovery", ip, dev.id)
                            if self.options.device:
                                self.setExitCode(3)
                            yield succeed(dev)
                            driver.next()
                            return
                        else:
                        # we continue on to model the device.
                            self.log.info("IP '%s' on device '%s' remodel",
                                          ip, dev.id)
                    self.sendDiscoveredEvent(ip, dev)
                
                # use the auto-allocate flag to change the device class
                # FIXME - this does not currently work
                newPath = self.autoAllocate(dev)
                if newPath:
                    yield self.config().callRemote(
                                    'moveDevice',dev.id,newPath)
                    driver.next()
                
                # the device that we found/created or that should be remodeled
                # is added to the list of devices to be modeled later
                if not self.options.nosnmp:
                    self.discovered.append(dev.id)
                yield succeed(dev)
                driver.next()
            except ZentinelException, e:
                self.log.exception(e)
                evt = dict(device=ip,
                           component=ip,
                           ipAddress=ip,
                           eventKey=ip,
                           eventClass=Status_Snmp,
                           summary=str(e),
                           severity=Info,
                           agent="Discover")
                if self.options.snmpMissing:
                    self.sendEvent(evt)
            except Exception, e:
                self.log.exception("Failed device discovery for '%s'", ip)
            self.log.debug("Finished scanning device with address %s", ip)

        return drive(inner)


    def collectNet(self, driver):
        """
        Twisted driver class to iterate through networks

        @param driver: Zenoss driver
        @type driver: Zenoss driver
        @return: successful result is a list of IPs that were added
        @rtype: Twisted deferred
        """

        import types
        # net option from the config file is a string
        if type(self.options.net) in types.StringTypes:
            self.options.net = [self.options.net]
        # in case someone uses 10.0.0.0,192.168.0.1 instead of 
        # --net 10.0.0.0 --net 192.168.0.1
        if isinstance(self.options.net, list) and \
               self.options.net[0].find(",") > -1:
            self.options.net = [
                n.strip() for n in self.options.net[0].split(',')
                ]
        count = 0
        devices = []
        if not self.options.net:
            yield self.config().callRemote('getDefaultNetworks')
            self.options.net = driver.next()

        if not self.options.net:
            self.log.warning("No networks configured")
            return
        
        for net in self.options.net:
            try:
                yield self.config().callRemote('getNetworks',
                                               net,
                                               self.options.subnets)
                nets = driver.next()
                if not nets:
                    self.log.warning("No networks found for %s" % (net,))
                    continue
                yield self.discoverIps(nets)
                ips = driver.next()
                devices += ips
                count += len(ips)
            except Exception, ex:
                self.log.exception("Error performing net discovery on %s", ex)
        def discoverDevice(ip):
            """
            Discover a particular device
            NB: Wrapper around self.discoverDevice()

            @param ip: IP address
            @type ip: string
            @return: Twisted/Zenoss Python iterable
            @rtype: Python iterable
            """
            return self.discoverDevice(ip, 
                                       self.options.deviceclass,
                                       self.options.productionState)
        yield NJobs(self.options.parallel, discoverDevice, devices).start()
        yield succeed("Discovered %d devices" % count)
        driver.next()


    def printResults(self, results):
        """
        Display the results that we've obtained

        @param results: what we've discovered
        @type results: string
        """
        if isinstance(results, Failure):
            self.log.error("Error: %s", results)
        else:
            self.log.info("Result: %s", results)
        self.main()


    def createDevice(self, driver):
        """
        Add a device to the system by name or IP.

        @param driver: driver object
        @type driver: Twisted/Zenoss object
        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        deviceName = self.options.device
        self.log.info("Looking for %s" % deviceName)
        ip = None
        if isip(deviceName):
            ip = deviceName
        else:
            try:
                # FIXME ZenUtils.IpUtil.asyncIpLookup is probably a better tool
                # for this, but it hasn't been tested, so it's for another day
                ip = socket.gethostbyname(deviceName)
            except socket.error: 
                ip = ""
        if not ip:
            raise NoIPAddress("No IP found for name %s" % deviceName)
        else:
            self.log.debug("Found IP %s for device %s" % (ip, deviceName))
            yield self.config().callRemote(
                                        'getDeviceConfig', [deviceName])
            me, = driver.next() or [None]
            if not me or self.options.remodel:
                yield self.discoverDevice(ip,
                                     devicepath=self.options.deviceclass,
                                     prodState=self.options.productionState)
                yield succeed("Discovered device %s." % deviceName)
                driver.next()


    def walkDiscovery(self, driver):
        """
        Python iterable to go through discovery

        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        myname = socket.getfqdn()
        self.log.debug("My hostname = %s", myname)
        myip = None
        try:
            myip = socket.gethostbyname(myname)
            self.log.debug("My IP address = %s", myip)
        except (socket.error, DNSNameError):
            self.log.warn("Failed lookup of my IP for name %s", myname)

        yield self.config().callRemote('getDeviceConfig', [myname])
        me, = driver.next() or [None]
        if not me or self.options.remodel:
            yield self.discoverDevice(myname, 
                                      devicepath=self.options.deviceclass, 
                                      prodState=self.options.productionState)
            me = driver.next()
        if not me:
            raise SystemExit("SNMP discover of self '%s' failed" % myname)
        if not myip:
            myip = me.manageIp
        if not myip: 
            raise SystemExit("Can't find my IP for name %s" % myname)

        yield self.discoverRouters(me, [myip])

        driver.next()
        if self.options.routersonly:
            self.log.info("Only routers discovered, skipping ping sweep.")
        else:
            yield self.config().callRemote('getSubNetworks')
            yield self.discoverIps(driver.next())
            ips = driver.next()
            if not self.options.nosnmp: 
                yield self.discoverDevices(ips)
                driver.next()


    def getDeviceList(self):
        """
        Our device list comes from our list of newly discovered devices

        @return: list of discovered devices
        @rtype: Twisted succeed() object
        """
        return succeed(self.discovered)


    def connected(self):
        """
        Called by Twisted once a connection has been established.
        """ 
        if self.options.walk:
            d = drive(self.walkDiscovery)
        
        elif self.options.device:
            d = drive(self.createDevice)
        
        else:
            d = drive(self.collectNet)

        d.addBoth(self.printResults)


    def autoAllocate(self, device=None):
        """
        Execute a script that will auto allocate devices into their 
        Device Classes

        @param device: device object
        @type device: device object
        @return: Device class path to put the new device
        @rtype: string
        @todo: make it actually work
        """
        self.log.debug("trying to auto-allocate device %s" % device.id )
        if not device:
            return
        script = getattr(device, "zAutoAllocateScript", None)
        self.log.debug("no auto-allocation script found")
        if script:
            import string
            script = string.join(script, "\n")
            self.log.debug("using script\n%s" % script)
            try:
                compile(script, "zAutoAllocateScript", "exec")
            except:
                self.log.error("zAutoAllocateScript contains error")
                return
            vars = {'dev': device, 'log': self.log}
            try:
                exec(script, vars)
            except:
                self.log.error(
                    "error executing zAutoAllocateScript:\n%s" % script)
            return vars.get('devicePath', None)
        return 


    def buildOptions(self):
        """
        Command-line option builder for optparse
        """
        ZenModeler.buildOptions(self)
        self.parser.add_option('--net', dest='net', action="append",  
                    help="Discover all device on this network")
        self.parser.add_option('--deviceclass', dest='deviceclass',
                    default="/Discovered",
                    help="Default device class for discovered devices")
        self.parser.add_option('--prod_state', dest='productionState',
                    default=1000,
                    help="Initial production state for discovered devices")
        self.parser.add_option('--remodel', dest='remodel',
                    action="store_true", default=False,
                    help="Remodel existing objects")
        self.parser.add_option('--routers', dest='routersonly',
                    action="store_true", default=False,
                    help="Only discover routers")
        self.parser.add_option('--tries', dest='tries', default=1, type="int",
                    help="How many ping tries")
        self.parser.add_option('--timeout', dest='timeout', 
                    default=2, type="float",
                    help="ping timeout in seconds")
        self.parser.add_option('--chunk', dest='chunkSize', 
                    default=10, type="int",
                    help="number of in flight ping packets")
        self.parser.add_option('--snmp-version', dest='zSnmpVer', 
                    help="SNMP version of the target")
        self.parser.add_option('--snmp-community', dest='zSnmpCommunity', 
                    help="SNMP community string of the target")
        self.parser.add_option('--snmp-port', dest='zSnmpPort', 
                    type="int", help="SNMP port of the target")
        self.parser.add_option('--snmp-missing', dest='snmpMissing',
                    action="store_true", default=False,
                    help="Send an event if SNMP is not found on the device")
        self.parser.add_option('--add-inactive', dest='addInactive',
                    action="store_true", default=False,
                    help="Add all IPs found, even if they are unresponsive")
        self.parser.add_option('--reset-ptr', dest='resetPtr',
                    action="store_true", default=False,
                    help="Reset all ip PTR records")
        self.parser.add_option('--no-snmp', dest='nosnmp',
                    action="store_true", default=False,
                    help="Skip SNMP discovery on found IP addresses")
        self.parser.add_option('--subnets', dest='subnets',
                    action="store_true", default=False,
                    help="Recurse into subnets for discovery")
        self.parser.add_option('--useFileDescriptor',
                    dest='useFileDescriptor', default=None,
                    help="Use the given (privileged) file descriptor for ping")
        self.parser.add_option('--assign-devclass-script', dest='autoAllocate',
                    action="store_true", default=False,
                    help="have zendisc auto allocate devices after discovery")
        self.parser.add_option('--walk', dest='walk', action='store_true',
                    default=False,
                    help="Walk the route tree, performing discovery on all networks")
        self.parser.add_option('--max-devices', dest='maxdevices',
                    default=0,
                    type='int',
                    help="Collect a maximum number of devices. Default is no limit.")
        self.parser.add_option('--snmp-strict-discovery', 
                    dest='zSnmpStrictDiscovery',
                    action="store_true", default=False,
                    help="Only add devices that can be modeled via snmp." )
        self.parser.add_option('--prefer-snmp-naming', 
                    dest='zPreferSnmpNaming',
                    action="store_true", default=False,
                    help="Prefer snmp name to dns name when modeling via snmp." )



if __name__ == "__main__":
    d = ZenDisc()
    d.processOptions()
    reactor.run = d.reactorLoop
    d.run()
