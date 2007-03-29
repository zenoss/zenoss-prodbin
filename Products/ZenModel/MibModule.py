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
from ZenPackable import ZenPackable

class MibModule(ZenModelRM, ZenPackable):

    language = ""
    contact = ""
    description = ""

    _properties = (
        {'id':'language', 'type':'string', 'mode':'w'},
        {'id':'contact', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
    )

    _relations = ZenPackable._relations + (
        ("miborganizer", ToOne(ToManyCont, "MibModule", "mibs")),
        ("nodes", ToManyCont(ToOne, "MibNode", "module")),
        ("notifications", ToManyCont(ToOne, "MibNotification", "module")),
    )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'immediate_view' : 'viewMibModule',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewMibModule'
                , 'permissions'   : ( Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
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

    def getModuleName(self): 
        return self.id

    
    def nodeCount(self):
        return self.nodes.countObjects()


    def notificationCount(self):
        return self.notifications.countObjects()

    
    def createMibNode(self, id, **kwargs):
        """Create a MibNode 
        """
        from MibNode import MibNode
        if self.oid2name(kwargs['oid']):
            return None
        node = MibNode(id, **kwargs) 
        self.nodes._setObject(node.id, node)
        node = self.nodes._getOb(node.id)
        return node 


    def createMibNotification(self, id, **kwargs):
        """Create a MibNotification 
        """
        from MibNotification import MibNotification
        if self.oid2name(kwargs['oid']):
            return None
        node = MibNotification(id, **kwargs) 
        self.notifications._setObject(node.id, node)
        node = self.notifications._getOb(node.id)
        return node 
        
    
    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        super(MibModule,self).manage_afterAdd(item, container)
        self.index_object()


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        super(MibModule,self).manage_afterClone(item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        super(MibModule,self).manage_beforeDelete(item, container)
        self.unindex_object()


InitializeClass(MibModule)
