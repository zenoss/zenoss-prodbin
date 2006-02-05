#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""UBRRouter

UBRRouter class represents a Ubr Router

$Id: UBRRouter.py,v 1.12 2004/04/12 16:20:44 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Router import Router
from IpAddress import findIpAddress

def manage_addUBRRouter(context, id, title = None, REQUEST = None):
    """make a device"""
    serv = UBRRouter(id, title)
    context._setObject(serv.id, serv)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addUBRRouter = DTMLFile('dtml/addUBRRouter',globals())


class UBRRouter(Router):
    """UBRRouter object"""
    portal_type = meta_type = 'UBRRouter'

    _relations = Router._relations + (
        ("dhcpservers", ToMany(ToMany, "Device", "dhcpubrclients")),
        )

    
    security = ClassSecurityInfo()
   
    def setDhcpHelpers(self, ips):
        dhcpservers = self.dhcpservers.objectValuesAll()
        sys = self.systems()
        if len(sys): sys = sys[0]
        else: sys = None
        for ip in ips:
            dip = findIpAddress(self, ip)
            if not dip: continue
            dserv = dip.getDevice()
            if dserv in dhcpservers: 
                dhcpservers.remove(dserv)
                continue
            if sys: dserv.addRelation("systems", sys)
            self.addRelation("dhcpservers", dserv)
        for dserv in dhcpservers:
            dserv.removeRelation("systems", sys)
            self.removeRelation("dhcpservers", dserv)


InitializeClass(UBRRouter)
