#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM

class MibModule(ZenModelRM):

    language = ""
    contact = ""
    description = ""

    _properties = (
        {'id':'language', 'type':'string', 'mode':'w'},
        {'id':'contact', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
    )

    _relations = (
        ("miborganizer", ToOne(ToManyCont, "MibModule", "mibs")),
        ("nodes", ToManyCont(ToOne, "MibNode", "module")),
        ("notifications", ToManyCont(ToOne, "MibNotification", "module")),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'editMibModule',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'editMibModule'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ( Permissions.view, )
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def nodeCount(self):
        return self.nodes.countObjects()


    def notificationCount(self):
        return self.notifications.countObjects()

    
    def createMibNode(self, id, **kwargs):
        """Create a MibModule 
        """
        from MibNode import MibNode
        node = MibNode(id, **kwargs) 
        self.nodes._setObject(node.id, node)
        return self.nodes._getOb(node.id)


    def createMibNotification(self, id, **kwargs):
        """Create a MibModule 
        """
        from MibNotification import MibNotification
        node = MibNotification(id, **kwargs) 
        self.notifications._setObject(node.id, node)
        return self.notifications._getOb(node.id)
        

InitializeClass(MibModule)
