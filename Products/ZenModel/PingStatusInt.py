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
        return self._pingStatus


    security.declareProtected('View', 'getDevicePingStatus')
    def getPingStatus(self):
        """get the ping status of the box if there is one"""
        ps = self._getPingStatusObj()
        if ps: return ps.getStatusString()
        return "No Status"


    security.declareProtected('View', 'getDevicePingStatusColor')
    def getPingStatusColor(self):
        """get the snmp status color of the device if there is one"""
        ps = self._getPingStatusObj()
        if ps: return ps.color()
        return ZenStatus.defaultColor


    security.declareProtected('View', 'getSnmpStatusNumber')
    def getPingStatusNumber(self):
        '''get a device's raw ping status number'''
        ps = self._getPingStatusObj()
        if ps: return ps.getStatus()
        return -1


    security.declareProtected('Manage Device Status', 'incrPingStatus')
    def incrPingStatus(self):
        """mark interface with failed ping"""
        ps = self._getPingStatusObj()
        if ps: return ps.incr()


    security.declareProtected('Manage Device Status', 'resetPingStatus')
    def resetPingStatus(self):
        """mark interface with working ping status"""
        ps = self._getPingStatusObj()
        if ps: return ps.reset()
       

    security.declareProtected('Manage Device Status', 'setPingStatus')
    def setPingStatus(self, value):
        """set the value of operational status based on ping"""
        ps = self._getPingStatusObj()
        if ps: return ps.setStatus(value)
   
    

InitializeClass(PingStatusInt)

