##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import logging
log = logging.getLogger("zen.triggers")

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AdministrativeRoleable import AdministrativeRoleable
from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER,
    NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE,
    NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE,
    TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION,
    UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD,
    ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE,
    ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE,
    ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS,
    ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE,
    ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER,
    ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT,
    ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE,
    ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER,
    ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE,
    ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS,
    ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW)
from Products.ZenRelations.RelSchema import (
    RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne)
from Products.ZenModel.ZenModelRM import ZenModelRM
from zope.interface import implements
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable


class InvalidTriggerActionType(Exception): pass

class DuplicateTriggerName(Exception): pass

def manage_addTriggerManager(context, REQUEST=None):
    """Create the trigger manager."""
    tm = TriggerManager(TriggerManager.root)
    context._setObject(TriggerManager.root, tm)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')

class TriggerManager(ZenModelRM):
    """Manage triggers."""

    _id = "TriggerManager"
    root = 'Triggers'
    meta_type = _id

    sub_meta_types = ("Trigger",)

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Management of triggers""",
            'icon'           : 'UserSettingsManager.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addTriggerManager',
            'immediate_view' : 'editSettings',
            'actions'        : (
                {
                    'id'            : 'settings',
                    'name'          : 'Settings',
                    'action'        : '../editSettings',
                    'permissions'   : ( ZEN_MANAGE_DMD, )
                })
         },
    )

addTrigger = DTMLFile('dtml/addTrigger',globals())


def manage_addTrigger(context, id, title = None, REQUEST = None):
    """Create a trigger"""
    ns = Trigger(id, title)
    context._setObject(id, ns)
    if REQUEST:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')

class Trigger(ZenModelRM, AdministrativeRoleable):
    """
    A stub object that is used for managing permissions.
    """
    implements(IGloballyIdentifiable)
    security = ClassSecurityInfo()

    _id = "Trigger"
    meta_type = _id

    _properties = ZenModelRM._properties

    _relations = (
        ("adminRoles",
        ToManyCont(
            ToOne,
            "Products.ZenModel.AdministrativeRole",
            "managedObject"
        )),
    )

    factory_type_information = (
        {
            'id'             : _id,
            'meta_type'      : _id,
            'description'    : """Stub object representing a trigger.""",
            'icon'           : 'ActionRule.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addTrigger',
            'immediate_view' : 'editTrigger',
            'actions'        :(
                {
                    'id'            : 'edit',
                    'name'          : 'Edit',
                    'action'        : 'editTrigger',
                    'permissions'   : (ZEN_CHANGE_ALERTING_RULES,)
                }
            )
         },
    )

    # a property storing user permission mappings
    users = []

    def __init__(self, id, title=None, buildRelations=True):
        self.globalRead = False
        self.globalWrite = False
        self.globalManage = False

        self.userRead = False
        self.userWrite = False
        self.userManage = False

        super(ZenModelRM, self).__init__(id, title=title, buildRelations=buildRelations)

    security.declareProtected(ZEN_CHANGE_ALERTING_RULES, 'manage_editTrigger')
    def manage_editTrigger(self, REQUEST=None):
        """Update trigger properties"""
        return self.zmanage_editProperties(REQUEST)

InitializeClass(TriggerManager)
InitializeClass(Trigger)
