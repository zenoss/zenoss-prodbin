##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from zope.interface import implements

from Products.ZenRelations.RelSchema import *
from Products.ZenWidgets import messaging

from Products.ZenModel.interfaces import IIndexed
from Products.ZenModel.ZenossSecurity import *
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable


class MibModule(ZenModelRM, ZenPackable):

    implements(IIndexed)
    types = ('COUNTER', 'GAUGE', 'DERIVE', 'ABSOLUTE')

    language = ""
    contact = ""
    description = ""

    _properties = (
        {'id':'language', 'type':'string', 'mode':'w'},
        {'id':'contact', 'type':'string', 'mode':'w'},
        {'id':'description', 'type':'string', 'mode':'w'},
    )

    _relations = ZenPackable._relations + (
        ("miborganizer", ToOne(ToManyCont, "Products.ZenModel.MibOrganizer", "mibs")),
        ("nodes", ToManyCont(ToOne, "Products.ZenModel.MibNode", "module")),
        ("notifications", ToManyCont(ToOne, "Products.ZenModel.MibNotification", "module")),
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


    def deleteMibNodes(self, ids=[], REQUEST=None):
        """Delete MibNodes 
        """
        for node in self.nodes():
            id = getattr(node, 'id', None)
            if id in ids:
                self.nodes._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Mappings Deleted',
                'Mib nodes deleted: %s' % (', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    def addMibNode(self, id, oid, nodetype, REQUEST=None):
        """Add a MibNode
        """
        node = self.createMibNode(id, oid=oid, nodetype=nodetype)
        if REQUEST:
            if node:
                messaging.IMessageSender(self).sendToBrowser(
                    'Mib Node Added',
                    'Node %s was created with oid %s.' % (id, oid)
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Invalid OID',
                    'OID %s is invalid.' % oid,
                    priority=messaging.WARNING
                )
            return self.callZenScreen(REQUEST)


    def createMibNode(self, id, **kwargs):
        """Create a MibNotification 
        """
        from MibNode import MibNode
        if self.oid2name(kwargs['oid'], exactMatch=True, strip=False):
            return None
        node = MibNode(id, **kwargs) 
        self.nodes._setObject(node.id, node)
        node = self.nodes._getOb(node.id)
        return node 


    def deleteMibNotifications(self, ids=[], REQUEST=None):
        """Delete MibNotifications 
        """
        for notification in self.notifications():
            id = getattr(notification, 'id', None)
            if id in ids:
                self.notifications._delObject(id)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Traps Deleted',
                'Traps deleted: %s' % (', '.join(ids))
            )
            return self.callZenScreen(REQUEST)


    def addMibNotification(self, id, oid, nodetype, REQUEST=None):
        """Add a MibNotification 
        """
        notification = self.createMibNotification(id, oid=oid, nodetype=nodetype)
        if REQUEST:
            if notification: 
                messaging.IMessageSender(self).sendToBrowser(
                    'Trap added',
                    'Trap %s was created with oid %s.' % (id, oid)
                )
            else:
                messaging.IMessageSender(self).sendToBrowser(
                    'Invalid OID',
                    'OID %s is invalid.' % oid,
                    priority=messaging.WARNING
                )
            return self.callZenScreen(REQUEST)


    def createMibNotification(self, id, **kwargs):
        """Create a MibNotification 
        """
        from MibNotification import MibNotification
        if self.oid2name(kwargs['oid'], exactMatch=True, strip=False):
            return None
        node = MibNotification(id, **kwargs) 
        self.notifications._setObject(node.id, node)
        node = self.notifications._getOb(node.id)
        return node
    

InitializeClass(MibModule)
