#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Router

Router class represents a server computer

$Id: Router.py,v 1.15 2004/04/12 16:20:44 edahl Exp $"""

__version__ = "$Revision: 1.15 $"[11:-2]

import re

from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import CMFCorePermissions

from Device import Device
from CricketRouter import CricketRouter

def manage_addRouter(context, id, title = None, REQUEST = None):
    """make a device"""
    serv = Router(id, title)
    context._setObject(serv.id, serv)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 


addRouter = DTMLFile('dtml/addRouter',globals())

class Router(CricketRouter,Device):
    """Router object"""
    portal_type = meta_type = 'Router'

    factory_type_information = ( 
        { 
            'id'             : 'Router',
            'meta_type'      : 'Router',
            'description'    : """Base class for all routers""",
            'icon'           : 'Router_icon.gif',
            'product'        : 'Confmon',
            'factory'        : 'manage_addRouter',
            'immediate_view' : 'viewRouterStatus',
            'actions'        :
               ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewRouterStatus'
                , 'permissions'   : (
                  CMFCorePermissions.View, )
                },
                { 'id'            : 'detail'
                , 'name'          : 'Detail'
                , 'action'        : 'viewDeviceDetail'
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
                , 'permissions'   : ("Change Device", )
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
            
InitializeClass(Router)
