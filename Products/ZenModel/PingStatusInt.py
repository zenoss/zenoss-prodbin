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

from Products.ZenEvents.ZenEventClasses import PingStatus

class PingStatusInt:

    security = ClassSecurityInfo()

    security.declareProtected('View', 'getDevicePingStatus')
    def getPingStatus(self):
        """get the ping status of the box if there is one"""
        return self.getStatus(PingStatus)
    security.declareProtected('View', 'getSnmpStatusNumber')
    getPingStatusNumber = getPingStatus


    security.declareProtected('View', 'getDevicePingStatus')
    def getPingStatusString(self):
        """get the ping status of the box if there is one"""
        return self.getStatusString(PingStatus)


InitializeClass(PingStatusInt)
