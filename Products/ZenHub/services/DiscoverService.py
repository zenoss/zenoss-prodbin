###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
log = logging.getLogger('zen.DiscoverService')

from Products.ZenUtils.IpUtil import numbip, strip
from Products.ZenEvents.Event import Event
from Products.ZenEvents.ZenEventClasses import Status_Ping
from Products.ZenModel.Device import manage_createDevice
from Products.ZenUtils.IpUtil import isip
from Products.ZenHub.PBDaemon import translateError

import transaction

from twisted.spread import pb
import socket
import math

from ModelerService import ModelerService

DEFAULT_PING_THRESH = 168


class IpNetProxy(pb.Copyable, pb.RemoteCopy):
    "A class that will represent a ZenModel/IpNetwork in zendisc"
    
    id = ''
    _children = None
    netmask = None

    def __init__(self, ipnet):
        self.id = ipnet.id
        self._children = map(IpNetProxy, ipnet.children())
        self.netmask = ipnet.netmask
        for prop in 'zAutoDiscover zDefaulNetworkTree zPingFailThresh'.split():
            if hasattr(ipnet, prop):
                setattr(self, prop, getattr(ipnet, prop))

    def children(self):
        return self._children

    def fullIpList(self):
        "copied from IpNetwork"
        if (self.netmask == 32): return [self.id]
        ipnumb = numbip(self.id)
        maxip = math.pow(2, 32 - self.netmask)
        start = int(ipnumb + 1)
        end = int(ipnumb + maxip - 1)
        return map(strip, range(start,end))

pb.setUnjellyableForClass(IpNetProxy, IpNetProxy)

class DiscoverService(ModelerService):

    @translateError
    def remote_getNetworks(self, net, includeSubNets):
        "Get network objects to scan"
        netObj = self.dmd.Networks.findNet(net, includeSubNets)
        if not netObj:
            return None
        nets = [netObj]
        if includeSubNets:
            nets += netObj.getSubNetworks()
        return map(IpNetProxy, nets)


    @translateError
    def remote_pingStatus(self, net, goodips, badips, resetPtr, addInactive):
        "Create objects based on ping results"
        net = self.dmd.Networks.findNet(net.id)
        pingthresh = getattr(net, "zPingFailThresh", DEFAULT_PING_THRESH)
        ips = []
        for ip in goodips:
            ipobj = net.createIp(ip)
            if resetPtr:
                ipobj.setPtrName()
            if not ipobj.device():
                ips.append(ip)
            if ipobj.getStatus(Status_Ping) > 0:
                self.sendIpStatusEvent(ipobj, sev=0)
        for ip in badips:
            ipobj = self.dmd.Networks.findIp(ip)
            if not ipobj and addInactive:
                ipobj = net.createIp(ip)
            if ipobj:
                if resetPtr:
                    ipobj.setPtrName()
                elif ipobj.getStatus(Status_Ping) > pingthresh:
                    net.ipaddresses.removeRelation(ipobj)
                if ipobj:
                    self.sendIpStatusEvent(ipobj)
        transaction.commit()
        return ips

                    
    def sendIpStatusEvent(self, ipobj, sev=2):
        """Send an ip down event.  These are used to cleanup unused ips.
        """
        ip = ipobj.id
        dev = ipobj.device()
        if sev == 0:
            msg = "ip %s is up" % ip
        else:
            msg = "ip %s is down" % ip
        if dev: 
            devname = dev.id
            comp = ipobj.interface().id
        else: 
            devname = comp = ip
        evt = Event(device=devname, ipAddress=ip, eventKey=ip,
                    component=comp, eventClass=Status_Ping,
                    summary=msg, severity=sev,
                    agent="Discover")
        self.dmd.ZenEventManager.sendEvent(evt)



    @translateError
    def remote_createDevice(self, ip, **kw):
        """Create a device.

        @param ip: The manageIp of the device
        @param kw: The args to manage_createDevice.
        """
        if not isip(ip):
            ip = socket.gethostbyname(ip)
        ipobj = self.dmd.Networks.findIp(ip)
        if not ipobj and not getattr(ipobj, "zAutoDiscover", True): 
            # self.log.info("ip '%s' on no auto-discover, skipping",ip)
            return
        if ipobj.device():
            return self.createDeviceProxy(ipobj.device()), False
        try:
            kw['manageIp'] = ip
            dev = manage_createDevice(self.dmd, **kw)
        except Exception, ex:
            raise pb.CopyableFailure(ex)
        transaction.commit()
        return self.createDeviceProxy(dev), True


    @translateError
    def remote_followNextHopIps(self, device):
        """
        Return the ips that the device's indirect routes point to
        which aren't currently connected to devices.
        """
        dev = self.dmd.Devices.findDevice(device)
        ips = []
        for r in dev.os.routes():
            ipobj = r.nexthop()
            if ipobj: ips.append(ipobj.id)
        return ips


    @translateError
    def remote_getSubNetworks(self):
        "Fetch proxies for all the networks"
        return map(IpNetProxy, self.dmd.Networks.getSubNetworks())


    @translateError
    def remote_getSnmpConfig(self, devicePath):
        "Get the snmp configuration defaults for scanning a device"
        devroot = self.dmd.Devices.createOrganizer(devicePath)
        return (devroot.zSnmpCommunities,
                devroot.zSnmpPort,
                devroot.zSnmpVer,
                devroot.zSnmpTimeout,
                devroot.zSnmpTries)
        

    @translateError
    def remote_moveDevice(self, dev, path):
        self.dmd.Devices.moveDevices(path, [dev])
        transaction.commit()

    @translateError
    def remote_getDefaultNetworks(self):
        monitor = self.dmd.Monitors.Performance._getOb(self.instance)
        return [net for net in monitor.discoveryNetworks]
