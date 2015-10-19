##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate

import Globals

import logging
log = logging.getLogger("zen.migrate")

from Products.ZenModel.ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW

class AdminObjectMenus(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):

        dmd.buildMenus(
            {'AdministeredObjects_list': [{
               'action': 'dialog_addAdministeredDevice',
                'description': 'Add Device...',
                'id': 'addAdministeredDevice',
                'isdialog': True,
                'ordering': 90.5,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredDeviceClass',
                'description': 'Add Device Class...',
                'id': 'addAdministeredDeviceClass',
                'isdialog': True,
                'ordering': 90.4,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredSystem',
                'description': 'Add System...',
                'id': 'addAdministeredSystem',
                'isdialog': True,
                'ordering': 90.3,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredGroup',
                'description': 'Add Group...',
                'id': 'addAdministeredGroup',
                'isdialog': True,
                'ordering': 90.2,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_addAdministeredLocation',
                'description': 'Add Location...',
                'id': 'addAdministeredLocation',
                'isdialog': True,
                'ordering': 90.1,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            },
            {  'action': 'dialog_deleteAdministeredObjects',
                'description': 'Delete Admin Objects...',
                'id': 'deleteAdministeredObjects',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_ADMIN_OBJECTS,)
            }],
            'UserSettings': [{ 'action': 'dialog_saveUserSettings',
                'description': 'Save User Settings...',
                'id': 'saveUserSettings',
                'isdialog': True,
                'ordering': 0.0,
                'permissions': (ZEN_CHANGE_SETTINGS,)
            }],
            'ActionRule_list': [  {  'action': 'dialog_addActionRule',
                'description': 'Add Alerting Rule...',
                'id': 'addActionRule',
                'isdialog': True,
                'ordering': 90.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)},
            {  'action': 'dialog_deleteActionRules',
                'description': 'Delete Rules...',
                'id': 'deleteActionRules',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)}],
           'ActionRuleWindow_list': [  {  'action': 'dialog_addActionRuleWindow',
                'description': 'Add Rule Window...',
                'id': 'addActionRuleWindow',
                'isdialog': True,
                'ordering': 90.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)},
           {  'action': 'dialog_deleteActionRuleWindows',
                'description': 'Delete Rule Windows...',
                'id': 'deleteActionRuleWindows',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_ALERTING_RULES,)}],
           'EventView_list': [  {  'action': 'dialog_addEventView',
                'description': 'Add Event View...',
                'id': 'addEventView',
                'isdialog': True,
                'ordering': 90.0,
                'permissions': (ZEN_CHANGE_EVENT_VIEWS,)},
           {  'action': 'dialog_deleteEventViews',
                'description': 'Delete Event Views...',
                'id': 'deleteEventViews',
                'isdialog': True,
                'ordering': 80.0,
                'permissions': (ZEN_CHANGE_EVENT_VIEWS,)}],
        })
        if hasattr(dmd.zenMenus.AdministeredObjects_list.zenMenuItems,
            'saveAdministeredObjects'):
            dmd.zenMenus.AdministeredObjects_list.manage_deleteZenMenuItem(
                'saveAdministeredObjects')


AdminObjectMenus()
