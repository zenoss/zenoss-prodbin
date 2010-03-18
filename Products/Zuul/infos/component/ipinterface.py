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
from Products.Zuul.infos.component import ComponentInfo
from Products.Zuul.interfaces import IIpInterfaceInfo
from Products.Zuul.decorators import info
from Products.Zuul.infos import ProxyProperty

def ipAddressVocab(context):
    return context.ips

class IpInterfaceInfo(ComponentInfo):
    implements(IIpInterfaceInfo)

    @info
    def getIpAddresses(self):
        return self._object.ipaddresses._objects.keys()
    def setIpAddresses(self, ips):
        self._object.setIpAddresses(ips)
    ipAddresses = property(getIpAddresses, setIpAddresses)

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

    interfaceName = ProxyProperty('interfaceName')
    ifindex = ProxyProperty('ifindex')
    macaddress = ProxyProperty('macaddress')
    type = ProxyProperty('type')
    mtu = ProxyProperty('mtu')
    speed = ProxyProperty('speed')
    adminStatus = ProxyProperty('adminStatus')
    operStatus = ProxyProperty('operStatus')
