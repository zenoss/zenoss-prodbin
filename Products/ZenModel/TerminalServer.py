#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""TerminalServer

TerminalServer class represents a TeriminalServer its
main function it to hold the relation Device to TerminalServer
a one to many.

$Id: TerminalServer.py,v 1.4 2004/04/12 16:20:44 edahl Exp $"""

__version__ = "$Revision: 1.4 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import CMFCorePermissions

from Router import Router
from IpAddress import findIpAddress

def manage_addTerminalServer(context, id, title = None, REQUEST = None):
    """make a device"""
    serv = TerminalServer(id, title)
    context._setObject(serv.id, serv)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addTerminalServer = DTMLFile('dtml/addTerminalServer',globals())


class TerminalServer(Router):
    """TerminalServer object"""
    portal_type = meta_type = 'TerminalServer'
    factory_type_information = ( 
        { 
            'id'             : 'TerminalServer',
            'meta_type'      : 'TerminalServer',
            'description'    : """Base class for all routers""",
            'icon'           : 'TerminalServer_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addTerminalServer',
            'immediate_view' : 'viewDeviceStatus',
            'actions'        :
               ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewDeviceStatus'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'detail'
                , 'name'          : 'Detail'
                , 'action'        : 'viewTerminalServerDetail'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewDevicePerformance'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },                
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'deviceEvents'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'deviceHistoryEvents'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editDevice'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'management'
                , 'name'          : 'Management'
                , 'action'        : 'deviceManagement'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()

InitializeClass(TerminalServer)
