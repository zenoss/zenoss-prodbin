#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceResult

A mixin for objects that get listed like devices
The primary object must implement getDevice.

$Id: DeviceResultInt.py,v 1.9 2004/04/23 01:24:48 edahl Exp $"""

__version__ = "$Revision: 1.9 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

class DeviceResultInt:
    
    security = ClassSecurityInfo()

    security.declareProtected('View', 'getDeviceName')
    def getDeviceName(self):
        '''Get the device name of this device or associated device'''
        d = self.getDevice()
        if d:
            return d._getDeviceName()
        return "No Device"


    security.declareProtected('View', 'getDeviceUrl')
    def getDeviceUrl(self):
        '''Get the primary url path of the device in which this
        interface is located'''
        d = self.getDevice()
        if d:
            return d.getPrimaryUrlPath()
        return ""


    security.declareProtected('View', 'getDeviceLink')
    def getDeviceLink(self):
        '''Get the primary link for the device'''
        d = self.getDevice()
        if d:
            return "<a href='%s'>%s</a>" % (d.getPrimaryUrlPath(), d.getId())
        return ""


    security.declareProtected('View', 'getDeviceClass')
    def getDeviceClassPath(self):
        '''Get the device class for this device'''
        d = self.getDevice()
        if d:
            return d._getDeviceClassPath()
        return "No Device"


    security.declareProtected('View', 'getDeviceProdState')
    def getProdState(self):
        '''Get the production state of the device associated with
        this interface'''
        d = self.getDevice()
        if d:
            return d._getProdState()
        return -1 


    security.declareProtected('View', 'getSnmpStatus')
    def getSnmpStatus(self):
        """get the snmp status of the box if there is one"""
        d = self.getDevice()
        if d:
            return d.getSnmpStatus()
        return "No Status"


    security.declareProtected('View', 'getSnmpStatusNumber')
    def getSnmpStatusNumber(self):
        """get the snmp status of the box if there is one"""
        d = self.getDevice()
        if d:
            return d.getSnmpStatusNumber()
        return -1

    
    security.declareProtected('View', 'getIp')
    def getDeviceIp(self):
        """Get the management ip (only) of a device"""
        d = self.getDevice()
        if d:
            int = d.getManageInterface()
            if int:
                return int.getIp()
        return ""


    security.declareProtected('View', 'getDeviceIpAddress')
    def getDeviceIpAddress(self):
        """Get the management ip with netmask (1.1.1.1/24) of a device"""
        d = self.getDevice()
        if d:
            int = d.getManageInterface()
            if int:
                return int.getIpAddress()
        return ""
           

    security.declareProtected('View', 'getDeviceMacaddress')
    def getDeviceMacaddress(self):
        """get the mac address if there is one of the primary interface"""
        d = self.getDevice()
        if d:
            int = d.getManageInterface()
            if int:
                return int.getInterfaceMacaddress()
        return ""
   
    
InitializeClass(DeviceResultInt)
