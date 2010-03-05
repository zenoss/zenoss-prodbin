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

from zope.interface import Attribute, Interface
from Products.Zuul.interfaces import IInfo


class IComponent(Interface):
    """
    An IComponent is a device component (an instance of OSComponent or
    HWComponent). Examples of device components are OSProcesses, IPServices and
    WinServices.
    """
    def device():
        """
        The parent device of this component.
        """

class IComponentInfo(IInfo):
    """
    An info adapter that wraps a device component.  Examples of device
    components are OSProcesses, IPServices and WinServices.
    """
    device = Attribute("The device associated with this component")
    monitored = Attribute("Is the instance monitored")
    status = Attribute("What is the status of the instance")


class IIpInterfaceInfo(IComponentInfo):
    """
    Info adapter for IPInterface components.
    """
    ips = Attribute("IP Addresses for this interface")
    ipAddress = Attribute("Primary IP address")
    interfaceName = Attribute("Interface name")
    macaddress = Attribute("MAC Address of this interface")
    type = Attribute("Type")
    mtu = Attribute("MTU")
    speed = Attribute("Speed")
    adminStatus = Attribute("Administrative status")
    operStatus = Attribute("Operational status")

