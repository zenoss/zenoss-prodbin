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
from Products.Zuul.form import schema


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
    device = schema.Entity(title=u"Parent Device",
                           description=u"The device associated with this component",
                           readonly=True, group="Overview")
    monitored = schema.Bool(title=u"Monitored",
                            description=u"Is the instance monitored",
                            group="Overview")
    status = schema.Text(title=u"Status",
                         description=u"Are there any active status events"
                         u" for this component?", group="Overview",
                         readonly=True)


class IIpInterfaceInfo(IComponentInfo):
    """
    Info adapter for IPInterface components.
    """
    ips = Attribute('IP Addresses')
    ipAddress = schema.Entity(title=u"IP Address",
                              description=u"Primary IP address",
                              group="Overview")
    interfaceName = schema.Text(title=u"Interface Name", group="Overview")
    macaddress = schema.Text(title=u"MAC Address", group="Overview")
    type = schema.Text(title=u"Type", group="Details", readonly=True)
    mtu = schema.Text(title=u"MTU", group="Details", readonly=True)
    speed = schema.Text(title=u"Speed", group="Details", readonly=True)
    adminStatus = schema.Text(title=u"Administrative Status", group="Details",
                             readonly=True)
    operStatus = schema.Text(title=u"Operational Status", group="Details",
                             readonly=True)

