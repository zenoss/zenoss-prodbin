###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements
from zope.component import adapts
from Products.Zuul.decorators import info
from Products.Zuul.interfaces import IComponentInfo, IComponent
from Products.Zuul.interfaces import IIpInterfaceInfo
from Products.Zuul.infos import InfoBase

class ComponentInfo(InfoBase):
    implements(IComponentInfo)
    adapts(IComponent)

    @property
    @info
    def device(self):
        return self._object.device()

    @property
    def locking(self):
        return {
            'updates': self._object.isLockedFromUpdates(),
            'deletion': self._object.isLockedFromDeletion(),
            'events': self._object.sendEventWhenBlocked()
        }

    @property
    def monitored(self):
        return self._object.monitor

    @property
    def status(self):
        statusCode = self._object.getStatus()
        return self._object.convertStatus(statusCode)


class IpInterfaceInfo(ComponentInfo):
    implements(IIpInterfaceInfo)

    @info
    def getIpAddresses(self):
        return self._object.ipaddresses()
    def setIpAddresses(self, ips):
        self._object.setIpAddresses(ips)
    ips = property(getIpAddresses, setIpAddresses)

    def _ipAddressObj(self):
        obj = self._object.getIpAddressObj()
        if obj is not None:
            return obj.primaryAq()

    @property
    @info
    def ipAddress(self):
        return self._ipAddressObj()

    @property
    @info
    def network(self):
        ipAddr = self._ipAddressObj()
        if ipAddr:
            return ipAddr.network().primaryAq()

    def getInterfaceName(self):
        return self._object.interfaceName
    def setInterfaceName(self, value):
        self._object.interfaceName = value
    interfaceName = property(getInterfaceName, setInterfaceName)

    def getIfIndex(self):
        return self._object.ifindex
    def setIfIndex(self, value):
        self._object.ifindex = value
    ifindex = property(getIfIndex, setIfIndex)

    def getMACAddress(self):
        return self._object.macaddress
    def setMACAddress(self, value):
        self._object.macaddress = value
    macaddress = property(getMACAddress, setMACAddress)

    def getType(self):
        return self._object.type
    def setType(self, value):
        self._object.type = value
    type = property(getType, setType)

    def getMTU(self):
        return self._object.mtu
    def setMTU(self, value):
        self._object.mtu = value
    mtu = property(getMTU, setMTU)

    def getSpeed(self):
        return self._object.speed
    def setSpeed(self, value):
        self._object.speed = value
    speed = property(getSpeed, setSpeed)

    def getAdminStatus(self):
        return self._object.adminStatus
    def setAdminStatus(self, value):
        self._object.adminStatus = value
    adminStatus = property(getAdminStatus, setAdminStatus)

    def getOperStatus(self):
        return self._object.operStatus
    def setOperStatus(self, value):
        self._object.operStatus = value
    operStatus = property(getOperStatus, setOperStatus)

