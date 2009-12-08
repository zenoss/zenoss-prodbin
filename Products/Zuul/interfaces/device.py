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

from zope.interface import Interface, Attribute
from Products.Zuul.interfaces import IInfo


class IDeviceClassNode(Interface):
    """
    Marker interface for device class nodes in a tree.
    """

class IDeviceClass(Interface):
    """
    Marker interface for DeviceClasses.
    """
    
class IDevice(Interface):
    """
    Marker interface for Device.
    """

class IDeviceClassInfo(Interface):
    """
    DeviceClass info
    """
    id = Attribute('Path of the device class')
    name = Attribute("Pretty name of the device class")

class IDeviceInfo(IInfo):
    """
    Device info
    """
    device = Attribute('The ID of the device')
    ipAddress = Attribute('The management IP address')
    productionState = Attribute('The production state of the device')
    events = Attribute('A list of (severity, count) tuples for the three most'
                       ' severe event severities')
    availability = Attribute('The availability percentage')
    
    def getDevice():
        """
        Returns the device attribute. Handy as a key when sorting a list of
        IDeviceInfos.
        """

class IDeviceClassFacade(Interface):

    def getInfo(root):
        """
        Get information about the DeviceClass identified by root.
        """

    def getDevices(root):
        """
        Get devices under root.
        """

