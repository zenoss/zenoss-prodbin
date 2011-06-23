###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
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
    device = Attribute("Parent Device")
    status = schema.TextLine(title=u"Status",
                             description=u"Are there any active status events"
                                         u" for this component?", group="Overview",
                             order=1,
                             readonly=True)
    usesMonitorAttribute = Attribute("Should the user be able to set the monitor attribute")
    monitor = Attribute("Has monitoring been enabled on the component")
    monitored = Attribute(u"Is the component being monitored"
                            u" (depends on the monitor setting and other"
                            u" factors). Empty string if not applicable.")


class IIpInterfaceInfo(IComponentInfo):
    """
    Info adapter for IPInterface components.
    """
    interfaceName = schema.TextLine(
        title=u"Interface Name", group="Overview",
        readonly=True, order=1)

    description = schema.Text(
        title=u"Description", group="Overview",
        readonly=True, order=2)

    adminStatus = schema.TextLine(
        title=u"Administrative Status", group="Overview",
        readonly=True, order=3)

    operStatus = schema.TextLine(
        title=u"Operational Status", group="Overview",
        readonly=True, order=4)

    status = schema.TextLine(
        title=u"Status", group="Overview",
        description=u"Are there any active status events for this component?"
                    u" for this component?",
        readonly=True, order=5)

    ipAddress = schema.Entity(
        title=u"IP Address (Primary)", group="Overview",
        description=u"Primary IP address",
        readonly=True, order=6)

    ipAddresses = schema.List(
        title=u'IP Addresses (All)', group="Details",
        readonly=True, order=7)

    macaddress = schema.TextLine(
        title=u"MAC Address", group="Details",
        readonly=True, order=8)

    type = schema.TextLine(
        title=u"Type", group="Details",
        readonly=True, order=9)

    speed = schema.TextLine(
        title=u"Speed", group="Details",
        readonly=True, order=10)

    duplex = schema.TextLine(
        title=u"Duplex Mode", group="Details",
        readonly=True, order=11)

    mtu = schema.TextLine(
        title=u"MTU", group="Details",
        readonly=True, order=12)


class IFileSystemInfo(IComponentInfo):
    """
    Info adapter for FileSystem components.
    """
    mount = schema.TextLine(title=u"Mount Point", group="Overview", order=-1)
    storageDevice = schema.TextLine(title=u"Storage Device", group="Details")
    type = schema.TextLine(title=u"Type", group="Details")
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
                                  readonly=True, order=-1)
    description = schema.Text(title=u"Description", group="Overview",
                              readonly=True, order=2)
    alertOnRestart = schema.Bool(title=u"Alert on Restart", group="Details",
                                 alwaysEditable=True)
    failSeverity = schema.Int(title=u"Fail Severity", xtype="severity",
                              group="Details", alwaysEditable=True)


class IWinServiceInfo(IComponentInfo):
    """
    Info adapter for WinService components.
    """
    serviceName = schema.Text(title=u"Name", group="Overview")
    serviceClass = schema.Entity(title=u"Service Class", group="Overview")
    caption = schema.TextLine(title=u"Caption", group="Overview")
    command = schema.TextLine(title=u"Command", group="Overview")
    failSeverity = schema.Int(title=u"Fail Severity", xtype="severity",
                              group="Details", alwaysEditable=True)
    serviceType = schema.TextLine(title=u"Service Type", group="Details")
    startMode = schema.TextLine(title=u"Start Mode", group="Details")
    startName = schema.TextLine(title=u"Start Name", group="Details")
    pathName = schema.TextLine(title=u"Path Name", group="Details")


class IIpServiceInfo(IComponentInfo):
    """
    Info adapter for IpService components
    """
    description = schema.Text(title=u"Description",
                              group="Overview")
    serviceClass = schema.Entity(title=u"Service Class", group="Overview")
    port = schema.Int(title=u"Port", group="Overview")
    protocol = schema.TextLine(title=u"Protocol", group="Details")
    ipaddresses = schema.List(title=u"IP Addresses", group="Details")
    manageIp = schema.Choice(title=u"Management IP Address",
                             vocabulary="serviceIpAddresses",
                             group="Overview")
    discoveryAgent = schema.TextLine(title=u"Discovery Agent", group="Details")
    failSeverity = schema.Int(title=u"Fail Severity", xtype="severity",
                              group="Details", alwaysEditable=True)
    sendString = schema.Text(title=u"Send String", group="Details")
    expectRegex = schema.TextLine(title=u"Expect Regex", group="Details")



class IIpRouteEntryInfo(IComponentInfo):
    """
    Info adapter for IpRouteEntry components.
    """
    destination = schema.Entity(title=u'Destination', readonly=True,
                                group="Overview")
    nextHop = schema.Entity(title=u"Next Hop", readonly=True, group="Overview")
    interface = schema.Entity(title=u"Interface", readonly=True,
                              group="Overview")
    protocol = schema.TextLine(title=u"Protocol", readonly=True, group="Overview")
    type = schema.TextLine(title=u"Type", readonly=True, group="Overview")


class ICPUInfo(IComponentInfo):
    """
    Info adapter for IpRouteEntry components.
    """
    socket = schema.Int(title=u"Socket", readonly=True)
    clockspeed = schema.Int(title=u"Clock Speed", readonly=True)
    extspeed = schema.Int(title=u"Ext Speed", readonly=True)
    voltage = schema.Int(title=u"Voltage", readonly=True)
    cacheSizeL1 = schema.Int(title=u"L1", readonly=True)
    cacheSizeL2 = schema.Int(title=u"L2", readonly=True)
    product = schema.Entity(title=u"Model", readonly=True)
    manufacturer = schema.Entity(title=u"Manufacturer", readonly=True)


class IExpansionCardInfo(IComponentInfo):
    """
    Info adapter for ExpansionCard components.
    """
    slot = schema.TextLine(title=u'Slot', group='Overview', readonly=True)
    serialNumber = schema.TextLine(title=u'Serial Number', readonly=True)
    product = schema.Entity(title=u'Model', readonly=True)
    manufacturer = schema.Entity(title=u'Manufacturer', readonly=True)


class IPowerSupplyInfo(IComponentInfo):
    """
    Info adapter for PowerSupply components.
    """
    watts = schema.Int(title=u'Watts', group='Overview', readonly=True)
    type = schema.TextLine(title=u'Type', group='Overview', readonly=True)
    state = schema.TextLine(title=u'State', group='Overview', readonly=True)
    millivolts = schema.Int(
        title=u'Millivolts', group='Overview', readonly=True)


class ITemperatureSensorInfo(IComponentInfo):
    """
    Info adapter for TemperatureSensor components.
    """
    state = schema.TextLine(title=u'State', group='Overview', readonly=True)
    temperature = schema.Int(
        title=u'Temperature (Fahrenheit)', group='Overview', readonly=True)


class IFanInfo(IComponentInfo):
    """
    Info adapter for Fan components.
    """
    state = schema.TextLine(title=u'State', group='Overview', readonly=True)
    type = schema.TextLine(title=u'Type', group='Overview', readonly=True)
    rpm = schema.Int(title=u'RPM', group='Overview', readonly=True)
