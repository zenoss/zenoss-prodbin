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
from Products.Zuul.utils import ZuulMessageFactory as _t

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
    device = Attribute("Parent Device")
    status = schema.Text(title=u"Status",
                         description=u"Are there any active status events"
                         u" for this component?", group="Overview",
                         order=1,
                         readonly=True)
    monitored = schema.Bool(title=u"Monitored",
                            order=0,
                            description=u"Is the instance monitored",
                            group="Overview")


class IIpInterfaceInfo(IComponentInfo):
    """
    Info adapter for IPInterface components.
    """
    description = schema.TextLine(title=u"Description",
                         order=2,
                         group="Overview")
    ipAddress = schema.Entity(title=u"IP Address",
                              description=u"Primary IP address",
                              group="Overview",
                              order=3)
    interfaceName = schema.Text(title=u"Interface Name", group="Overview",
                                order=-1)
    macaddress = schema.Text(title=u"MAC Address", group="Details")
    type = schema.Text(title=u"Type", group="Details")
    mtu = schema.Text(title=u"MTU", group="Details")
    speed = schema.Text(title=u"Speed", group="Details")
    ipAddresses = schema.List(title=u'IP Addresses', group="Details")
    adminStatus = schema.Int(title=u"Administrative Status",
                                group="Details", xtype="updownfield")
    operStatus = schema.Int(title=u"Operational Status", group="Details",
                               xtype="updownfield")


class IFileSystemInfo(IComponentInfo):
    """
    Info adapter for FileSystem components.
    """
    mount = schema.Text(title=u"Mount Point", group="Overview", order=-1)
    storageDevice = schema.Text(title=u"Storage Device", group="Details")
    type = schema.Text(title=u"Type", group="Details")
    blockSize = schema.Int(title=u"Block Size", group="Details")
    totalBlocks = Attribute("Total Blocks")
    totalBytes = schema.Int(title=u"Total Bytes", readonly=True,
                            group="Details")
    usedBytes = schema.Int(title=u"Used Bytes", readonly=True, group="Details")
    availableBytes = schema.Int(title=u"Available Bytes", readonly=True,
                                group="Details")
    capacityBytes = schema.Int(u"Capacity Bytes", readonly=True,
                               group="Details")
    totalFiles = schema.Int(title=u"Total Files", group="Details")
    availableFiles = schema.Int(title=u"Available Files", readonly=True,
                                group="Details")
    capacityFiles = schema.Int(title=u"Capacity Files", readonly=True,
                               group="Details")
    maxNameLength = schema.Int(title=u"Maximum Name Length", group="Details")


class IOSProcessInfo(IComponentInfo):
    """
    Info adapter for OSProcess components.
    """
    processClass = schema.Entity(title=u"Process Class", group="Overview",
                                 order=1)
    processName = schema.TextLine(title=u"Process Name", group="Overview",
                                  order=-1)
    alertOnRestart = schema.Bool(title=u"Alert on Restart", group="Details")
    failSeverity = schema.Int(title=u"Fail Severity", xtype="Severity",
                              group="Details")


class IWinServiceInfo(IComponentInfo):
    """
    Info adapter for WinService components.
    """
    description = schema.TextLine(title=u"Description",
                         group="Overview")
    serviceClass = schema.Entity(title=u"Service Class", group="Overview")
    command = schema.Text(title=u"Command", group="Overview")
    failSeverity = schema.Int(title=u"Fail Severity", xtype="Severity",
                              group="Details")
    serviceType = schema.Text(title=u"Service Type", group="Details")
    startMode = schema.Text(title=u"Start Mode", group="Details")
    startName = schema.Text(title=u"Start Name", group="Details")
    acceptPause = schema.Bool(title=u"Accept Pause", group="Details")
    acceptStop = schema.Bool(title=u"Accept Stop", group="Details")
    pathName = schema.Text(title=u"Path Name", group="Details")


class IIpServiceInfo(IComponentInfo):
    """
    Info adapter for IpService components
    """
    description = schema.TextLine(title=u"Description",
                         group="Overview")
    serviceClass = schema.Entity(title=u"Service Class", group="Overview")
    port = schema.Int(title=u"Port", group="Overview")
    protocol = schema.Text(title=u"Protocol", group="Details")
    ipaddresses = schema.List(title=u"IP Addresses", group="Details")
    manageIp = schema.Choice(title=u"Management IP Address",
                             vocabulary="serviceIpAddresses",
                             group="Overview")
    discoveryAgent = schema.Text(title=u"Discovery Agent", group="Details")
    sendString = schema.TextLine(title=u"Send String", group="Details")
    expectRegex = schema.Text(title=u"Expect Regex", group="Details")



class IIpRouteEntryInfo(IComponentInfo):
    """
    Info adapter for IpRouteEntry components.
    """
    destination = schema.Entity(title=u'Destination', readonly=True,
                                group="Overview")
    nextHop = schema.Entity(title=u"Next Hop", readonly=True, group="Overview")
    interface = schema.Entity(title=u"Interface", readonly=True,
                              group="Overview")
    protocol = schema.Text(title=u"Protocol", readonly=True, group="Overview")
    type = schema.Text(title=u"Type", readonly=True, group="Overview")


