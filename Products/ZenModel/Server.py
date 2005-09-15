#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Server

Server class represents a server computer

$Id: Server.py,v 1.24 2004/04/14 22:11:48 edahl Exp $"""

__version__ = "$Revision: 1.24 $"[11:-2]

import re

from Globals import DTMLFile
from Globals import InitializeClass

from Products.CMFCore import permissions

from Device import Device
from CricketServer import CricketServer

def manage_addServer(context, id, title = None, REQUEST = None):
    """make a device"""
    serv = Server(id, title)
    context._setObject(serv.id, serv)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addServer = DTMLFile('dtml/addServer',globals())

class Server(CricketServer, Device):
    """Server object"""
    portal_type = meta_type = 'Server'
    
    _properties = (Device._properties + 
                   (
                    {'id':'sshVersion', 'type':'int', 'mode':'w'},
                    {'id':'snmpSysedgeMode', 'type':'string', 'mode':''},
                   ))

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Server',
            'meta_type'      : 'Server',
            'description'    : """Class representing a server computer""",
            'icon'           : 'Server_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addServer',
            'immediate_view' : 'viewDeviceStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewDeviceStatus'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'detail'
                , 'name'          : 'Detail'
                , 'action'        : 'viewServerDetail'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewServerPerformance'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'deviceEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'deviceHistoryEvents'
                , 'permissions'   : (
                  permissions.View, )
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
                  permissions.View, )
                },
            )
         },
        )


    def __init__(self, id, sshVersion = 2):
        Device.__init__(self, id)
        self.sshVersion = sshVersion
        self.snmpSysedgeMode = ""



    def summary(self):
        sumtext = Device.summary(self)
        return (self.snmpAgent + " " + 
                self.snmpSysedgeMode + " " +
                sumtext)


InitializeClass(Server)
