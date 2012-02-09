###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import Interface

class ICallHomeCollector(Interface):
    """
    Implementers provide call home data
    """

    def generateData(self):
        """
        Generate data to be sent via call home
        @return: dictionary of data to be sent
        @rtype: dict
        """

class IMasterCallHomeCollector(Interface):
    """
    Implementers provide call home data when collected on zenoss master
    """

    def generateData(self, dmd):
        """
        Generate data to be sent via call home
        @param dmd: databse connection
        @return: dictionary of data to be sent
        @rtype: dict
        """

class IHostData(Interface):
    """
    Used to gather Host machine statistics for call home
    """

    def callHomeData(self):
        """
        @return:: name, value pairs of host stats for call home
        @rtype: list or generator of tuples
        """


class IZenossData(Interface):
    """
    Used to gather Zenoss statistics for call home
    """

    def callHomeData(self, dmd):
        """
        @param: dmd connection
        @return: name, value pairs of Zenoss instance stats for call home
        @rtype: list or generator of tuples
        """


class IZenossEnvData(Interface):
    """
    Used to gather the Zenoss environment data for call home
    """

    def callHomeData(self):
        """
        @return: name, value pairs of host stats for call home
        @rtype: list or generator of tuples
        """


class IDeviceResource(Interface):
    """
    Subscription Adapter to Provide more resource data about a device
    """

    def processDevice(self, stats):
        """
        Determine any resource metrics about the device and add or update the passed in stats dictionary
        @param: stats - statistics about the device
        @type: dictionary
        @return: None
        """


class IDeviceType(Interface):
    """
    Adapter to determine the type of device. examples: Xen, VMware, Physical etc...
    """

    def type(self):
        """
        @return: type of device. example: "VMware", "Xen", "Physical
        @rtype: str
        """

    def isVM(self):
        """
        @return: True if device is a vm, false otherwise
        @rtype: bool
        """


class IVirtualDeviceType(Interface):
    """
    Subscription adapter. Determine the virtual machine type of a device if any. More than one impl can be
    registered per Device
    """
    def vmType(self):
        """
        @return the type of virtual machine or None if not a virtual machine or it cannot be determined
        """


class IDeviceCpuCount(Interface):
    """
    Adapter to Provide more cpu count for a device
    """

    def cpuCount(self):
        """
        Determine number of CPUs on a device
        @return: number of cpus
        @rtype: int
        """
