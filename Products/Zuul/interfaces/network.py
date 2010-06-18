###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Attribute
from Products.Zuul.interfaces import IInfo, IFacade
from Products.Zuul.interfaces.tree import ITreeNode

class IIpNetworkNode(ITreeNode):
    """
    Marker interface for an IpNetwork tree node.
    """

class INetworkFacade(IFacade):
    pass

class IIpNetworkInfo(IInfo):
    """
    Info wrapper for IpNetwork objects.
    """
    name = Attribute('The name of a network')
    description = Attribute('A description of a network')
    ipcount = Attribute('The number of total and free IPs in a network')

    isInheritAutoDiscover = Attribute('Does network inherit AutoDiscover property')
    autoDiscover = Attribute('zAutoDiscover')

    isInheritDefaultNetworkTree = Attribute('Does network inherit DefaultNetworkTree property')
    defaultNetworkTree = Attribute('zDefaultNetworkTree')

    isInheritDrawMapLinks = Attribute('Does network inherit DrawMapLinks property')
    drawMapLinks = Attribute('zDrawMapLinks')

    isInheritIcon = Attribute('Does network inherit Icon property')
    icon = Attribute('zIcon')

    isInheritPingFailThresh = Attribute('Does network inherit PingFailThresh property')
    pingFailThresh = Attribute('zPingFailThresh')

    isInheritPreferSnmpNaming = Attribute('Does network inherit PreferSnmpNaming property')
    autoDiscover = Attribute('zPreferSnmpNaming')

    isInheritSnmpStrictDiscovery = Attribute('Does network inherit SnmpStrictDiscovery property')
    SnmpStrictDiscovery = Attribute('zSnmpStrictDiscovery')

class IIpAddressInfo(IInfo):
    pass
