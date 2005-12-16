#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
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

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Device import Device
from IpAddress import findIpAddress

def manage_addTerminalServer(context, id, title = None, REQUEST = None):
    """make a device"""
    serv = TerminalServer(id, title)
    context._setObject(serv.id, serv)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addTerminalServer = DTMLFile('dtml/addTerminalServer',globals())


class TerminalServer(Device):
    """TerminalServer object"""

    portal_type = meta_type = 'TerminalServer'

    _relations = Device._relations + (
        ("devices", ToMany(ToOne, "Device", "termserver")),
        )

    factory_type_information = ( 
        { 
            'id'             : 'TerminalServer',
            'meta_type'      : 'TerminalServer',
            'description'    : """Base class for all TerminalServers""",
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
                  permissions.view, )
                },
                { 'id'            : 'detail'
                , 'name'          : 'Detail'
                , 'action'        : 'viewTerminalServerDetail'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewDevicePerformance'
                , 'permissions'   : (
                  permissions.view, )
                },                
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'viewHistoryEvents'
                , 'permissions'   : (
                  permissions.view, )
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
                  permissions.view, )
                },
            )
         },
        )
    
    security = ClassSecurityInfo()

InitializeClass(TerminalServer)
