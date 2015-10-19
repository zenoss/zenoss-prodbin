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

from Products.ZenRelations.RelSchema import RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne
from Products.ZenWidgets import messaging

from Products.ZenModel.interfaces import IIndexed
from Products.ZenModel.ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW
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
