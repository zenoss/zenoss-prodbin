###############################################################################
#
#   Copyright (c) 2004 Zentinel Systems. 
#
###############################################################################

__doc__="""PingStatusInt

Interface for all objects that track their ping status 
(Device, IpAddress, IpInterface)

$Id: PingStatusInt.py,v 1.3 2004/04/23 01:24:49 edahl Exp $"""

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

import ZenStatus

class PingStatusInt:

    security = ClassSecurityInfo()

    def _getPingStatusObj(self):
        if (not hasattr(self, "_pingStatus") 
            or getattr(self, "_pingStatus") == None):
            self._pingStatus = ZenStatus.ZenAvailibility(-1)
        return self._pingStatus


    security.declareProtected('View', 'getDevicePingStatus')
    def getPingStatus(self):
        """get the ping status of the box if there is one"""
        ps = self._getPingStatusObj()
        if ps:
            return ps.getStatusString()
        return "No Status"


    def getPingAvail30(self):
        """30 day rolling ping availability"""
        ps = self._getPingStatusObj()
        if ps:
            return ps.getAvail30()
        return -1

            
    def getPingAvail30String(self):
        """30 day rolling ping availability"""
        ps = self._getPingStatusObj()
        if ps:
            return ps.getAvail30String()
        return "Unknown"

            
    security.declareProtected('View', 'getDevicePingStatusColor')
    def getPingStatusColor(self):
        """get the snmp status color of the device if there is one"""
        ps = self._getPingStatusObj()
        if ps:
            return ps.color()
        return ZenStatus.defaultColor


    security.declareProtected('View', 'getSnmpStatusNumber')
    def getPingStatusNumber(self):
        '''get a device's raw ping status number'''
        ps = self._getPingStatusObj()
        if not ps: return -1
        return ps.getStatus()


    security.declareProtected('Change Device', 'incrPingStatus')
    def incrPingStatus(self):
        """mark interface with failed ping"""
        ps = self._getPingStatusObj()
        if ps: return ps.incr()


    security.declareProtected('Change Device', 'resetPingStatus')
    def resetPingStatus(self):
        """mark interface with working ping status"""
        ps = self._getPingStatusObj()
        if ps: return ps.reset()
       

    security.declareProtected('Change Device', 'setPingStatus')
    def setPingStatus(self, value):
        """set the value of operational status based on ping"""
        ps = self._getPingStatusObj()
        if ps: ps.setStatus(value)
   
    

InitializeClass(PingStatusInt)

