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

import socket

import Globals

from Products.ZenUtils.Exceptions import ZentinelException
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.Driver import drive
from Products.ZenUtils.IpUtil import asyncNameLookup
from Products.ZenUtils.NJobs import NJobs
from Products.ZenEvents.ZenEventClasses import Status_Snmp
from Products.ZenEvents.Event import Info
from Products.ZenStatus.AsyncPing import Ping
from Products.ZenHub.PBDaemon import FakeRemote, PBDaemon
from Products.ZenHub.services  import DiscoverService, ModelerService
unused(DiscoverService, ModelerService) # for pb

from zenmodeler import ZenModeler

from twisted.internet.defer import succeed
from twisted.python.failure import Failure
from twisted.internet import reactor
from twisted.names.error import DNSNameError


class ZenDisc(ZenModeler):
    "Scan networks and routes looking for devices to add to the Model"

    initialServices = PBDaemon.initialServices + ['DiscoverService']
    name = 'zendisc'
    scanned = 0

    def __init__(self,noopts=0,app=None,single=True, keeproot=True):
        ZenModeler.__init__(self, noopts, app, single, keeproot)
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
        "Get the DiscoverService"
        return self.services.get('DiscoverService', FakeRemote())

    def discoverIps(self, nets):
        """Ping all ips, create entries in the network if nessesary.

        @return deferred: successful result is a list of IPs that were added
        """
        def inner(driver):
            ips = []
            goodCount = 0
            ips = []
            # it would be nice to interleave ping/discover
            for net in nets:
                if self.options.subnets and len(net.children()) > 0:
                    continue
                if not getattr(net, "zAutoDiscover", False): 
                    self.log.warn("skipping network %s zAutoDiscover is False"
                                  % net.id)
                    continue
                self.log.info("discover network '%s'", net.id)
                yield NJobs(self.options.chunkSize,
                            self.ping.ping,
                            net.fullIpList()).start()
                results = driver.next()
                goodips = [
                    v.ipaddr for v in results if not isinstance(v, Failure)]
                badips = [
                    v.value.ipaddr for v in results if isinstance(v, Failure)]
                goodCount += len(goodips)
                self.log.debug("Got %d good ips and %d bad ips",
                               len(goodips), len(badips))
                yield self.config().callRemote('pingStatus',
                                               net,
                                               goodips,
                                               badips,
                                               self.options.resetPtr,
                                               self.options.addInactive)
                ips += driver.next()
                self.log.info("discovered %s active ips", goodCount)
            # make sure this is the return result for the driver
            yield succeed(ips)
            driver.next()
        d = drive(inner)
        return d
       

    def discoverRouters(self, rootdev, seenips=None):
        """Discover all default routers based on dmd configuration.
        """
        if not seenips:
            seenips = []
        def inner(driver):
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
        """Send an device discovered event.
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
        """Discover devices by active ips that are not associated with a device.
        """
        def discoverDevice(ip):
            return self.discoverDevice(ip, devicepath, prodState)
        return NJobs(self.options.parallel, discoverDevice, ips).start()

    def findRemoteDeviceInfo(self, ip, devicePath):
        """Scan a device for ways of naming it: PTR DNS record or a SNMP name

        @return deferred: result is None or
                a tuple containing (community, port, version, snmp name)
        """
        from pynetsnmp.twistedsnmp import AgentProxy
        def inner(driver):
            self.log.debug("Doing SNMP lookup on device %s", ip)
            yield self.config().callRemote('getSnmpConfig', devicePath)
            communities, port, version, timeout, retries = driver.next()
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
        """Discover a device based on its ip address.
        """
        self.scanned += 1
        if self.options.maxdevices:
            if self.scanned >= self.options.maxdevices:
                self.log.info("Limit of %d devices reached" %
                              self.options.maxdevices)
                return succeed(None)
        def inner(driver):
            try:
                name = ip
                kw = dict(deviceName=name,
                          discoverProto=None,
                          devicePath=devicepath,
                          performanceMonitor=self.options.monitor)
                if not self.options.nosnmp:
                    self.log.debug("Scanning device with address %s", ip)
                    yield self.findRemoteDeviceInfo(ip, devicepath)
                    deviceInfo = driver.next()
                    if deviceInfo:
                        community, port, ver, snmpname = deviceInfo
                        kw.update(dict(deviceName=snmpname,
                                       zSnmpCommunity=community,
                                       zSnmpPort=port,
                                       zSnmpVer=ver))
                yield asyncNameLookup(ip)
                try:
                    kw.update(dict(deviceName=driver.next()))
                except Exception, ex:
                    self.log.debug("Failed to lookup %s (%s)" % (ip, ex))
                yield self.config().callRemote('createDevice', ip, **kw)
                result = driver.next()
                if isinstance(result, Failure):
                    raise ZentinelException(result.value)
                dev, created = result
                newPath = self.autoAllocate(dev)
                if newPath:
                    yield self.config().callRemote('moveDevice', dev.id, newPath)
                    drive.next()
                if not dev:
                    self.log.info("ip '%s' on no auto-discover, skipping",ip)
                else:
                    if not created:
                        if not self.options.remodel:
                            self.log.info("ip '%s' on device '%s' skipping",
                                          ip, dev.id)
                            yield succeed(dev)
                            driver.next()
                            return
                        else:
                            self.log.info("ip '%s' on device '%s' remodel",
                                          ip, dev.id)
                    self.sendDiscoveredEvent(ip, dev)
                if not self.options.nosnmp:
                    self.discovered.append(dev.id)
                yield succeed(dev)
                driver.next()
            except ZentinelException, e:
                self.log.warn(e)
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
                self.log.exception("failed device discovery for '%s'", ip)
            self.log.debug("Finished scanning device with address %s", ip)
        return drive(inner)


    def collectNet(self, driver):
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
            return self.discoverDevice(ip, 
                                       self.options.deviceclass,
                                       self.options.productionState)
        yield NJobs(self.options.parallel, discoverDevice, devices).start()
        yield succeed("Discovered %d devices" % count)
        driver.next()

    def printResults(self, results):
        if isinstance(results, Failure):
            self.log.error("Error: %s", results)
        else:
            self.log.info("Result: %s", results)
        self.main()

    def walkDiscovery(self, driver):
        myname = socket.getfqdn()
        self.log.info("my hostname = %s", myname)
        myip = None
        try:
            myip = socket.gethostbyname(myname)
            self.log.info("my ip = %s", myip)
        except (socket.error, DNSNameError):
            self.log.warn("failed lookup of my ip for name %s", myname)
        yield self.config().callRemote('getDeviceConfig', [myname])
        me, = driver.next() or [None]
        if not me or self.options.remodel:
            yield self.discoverDevice(myname, 
                                      devicepath=self.options.deviceclass, 
                                      prodState=self.options.productionState)
            me = driver.next()
        if not me:
            raise SystemExit("snmp discover of self '%s' failed" % myname)
        if not myip:
            myip = me.manageIp
        if not myip: 
            raise SystemExit("can't find my ip for name %s" % myname)
        yield self.discoverRouters(me, [myip])
        driver.next()
        if self.options.routersonly:
            self.log.info("only routers discovered, skipping ping sweep.")
        else:
            yield self.config().callRemote('getSubNetworks')
            yield self.discoverIps(driver.next())
            ips = driver.next()
            if not self.options.nosnmp: 
                yield self.discoverDevices(ips)
                driver.next()

    def getDeviceList(self):
        "Our device list comes from our list of newly discovered devices"
        return succeed(self.discovered)

    def connected(self):
        self.log.info('connected to ZenHub')
        if self.options.walk:
            d = drive(self.walkDiscovery)
        else:
            d = drive(self.collectNet)
        d.addBoth(self.printResults)

    def autoAllocate(self, device=None):
	"""Execute a script that will auto allocate devices into their 
	Device Classes"""
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
		self.log.error("error executing zAutoAllocateScript:\n%s" % script)
		return vars.get('devicePath', None)
	return 


    def buildOptions(self):
        ZenModeler.buildOptions(self)
        self.parser.add_option('--net', dest='net', action="append",  
                    help="discover all device on this network")
        self.parser.add_option('--deviceclass', dest='deviceclass',
                    default="/Discovered",
                    help="default device class for discovered devices")
        self.parser.add_option('--prod_state', dest='productionState',
                    default=1000,
                    help="initial production state for discovered devices")
        self.parser.add_option('--remodel', dest='remodel',
                    action="store_true", default=False,
                    help="remodel existing objects")
        self.parser.add_option('--routers', dest='routersonly',
                    action="store_true", default=False,
                    help="only discover routers")
        self.parser.add_option('--tries', dest='tries', default=1, type="int",
                    help="how many ping tries")
        self.parser.add_option('--timeout', dest='timeout', 
                    default=2, type="float",
                    help="ping timeout in seconds")
        self.parser.add_option('--chunk', dest='chunkSize', 
                    default=10, type="int",
                    help="number of in flight ping packets")
        self.parser.add_option('--snmp-missing', dest='snmpMissing',
                    action="store_true", default=False,
                    help="send an event if SNMP is not found on the device")
        self.parser.add_option('--add-inactive', dest='addInactive',
                    action="store_true", default=False,
                    help="add all IPs found, even if they are unresponsive")
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
                    help="Use the given (priveleged) file descriptor for ping")

        self.parser.add_option('--auto-allocate', dest='autoAllocate',
                    action="store_true", default=False,
                    help="have zendisc auto allocate devices after discovery")
        self.parser.add_option('--walk', dest='walk', action='store_true',
                    default=False,
                    help="Walk the route tree, performing discovery on all networks")
        self.parser.add_option('--max-devices', dest='maxdevices',
                    default=0,
                    type='int',
                    help="Collect a maximum number of devices. Default is no limit.")



if __name__ == "__main__":
    d = ZenDisc()
    d.processOptions()
    reactor.run = d.reactorLoop
    d.run()
