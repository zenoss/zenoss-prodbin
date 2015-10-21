##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
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
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import (
    RELMETATYPES, RelSchema, ToMany, ToManyCont, ToOne)
from ZenPackable import ZenPackable


manage_addUserCommand = DTMLFile('dtml/addUserCommand',globals())


class UserCommand(ZenModelRM, ZenPackable):

    meta_type = 'UserCommand'

    security = ClassSecurityInfo()

    description = ""
    command = ''

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        {'id':'command', 'type':'text', 'mode':'w'},
        )

    _relations =  ZenPackable._relations + (
        ("commandable", ToOne(
                ToManyCont, 'Products.ZenModel.Commandable', 'userCommands')),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = (
    {
        'immediate_view' : 'userCommandDetailNew',
        'actions'        :
        (
            {'id'            : 'overview',
             'name'          : 'User Command',
             'action'        : 'userCommandDetailNew',
             'permissions'   : ( Permissions.view, ),
            },
        )
    },
    )

    security.declareProtected('View', 'breadCrumbs')
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object
        [('url','id'), ...]
        """
        crumbs = super(UserCommand, self).breadCrumbs(terminator)
        aqParent = self.getPrimaryParent()
        while aqParent.meta_type == 'ToManyContRelationship':
            aqParent = aqParent.getPrimaryParent()
        url = aqParent.absolute_url_path() + '/dataRootManage'
        return [(url, 'Commands')]

    def updateUserCommand(self, params):
        """
        params
        self.description
        self.command
        """
        self.command = params['command']
        self.description = params['description']


InitializeClass(UserCommand)
