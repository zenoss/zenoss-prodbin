#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Location

Location is a base class that represents a physical
location where a collection of devices resides.

$Id: LocationBase.py,v 1.4 2004/04/09 00:34:39 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from Globals import InitializeClass

from Products.ZenUtils.Utils import travAndColl

from Instance import Instance
from DeviceGroupInt import DeviceGroupInt

class LocationBase(Instance, DeviceGroupInt):
    """Location object"""
    portal_type = meta_type = 'LocationBase'
    

    def pingStatus(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupInt.pingStatus(self, "sublocations")

    
    def snmpStatus(self):
        """aggrigate snmp status for all devices in this group and below"""
        return DeviceGroupInt.snmpStatus(self, "sublocations")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceGroupInt.getSubDevices(self, filter, "sublocations")


    def getLocationName(self):
        """return the full name of a location (take out relation from path)"""
        return DeviceGroupInt.getDeviceGroupName(self, "location")

    getPathName = getLocationName


    def getLocationNames(self):
        """build a list of the full paths of all sub locations""" 
        locnames = [self.getLocationName()]
        for subloc in self.sublocations():
            locnames.extend(subloc.getLocationNames())
        return locnames
   

InitializeClass(LocationBase)
