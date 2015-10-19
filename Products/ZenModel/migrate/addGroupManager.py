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
from Products.PluggableAuthService import plugins
from Products.ZenModel.ZenossSecurity import MANAGER_ROLE, MANAGE_NOTIFICATION_SUBSCRIPTIONS, MANAGE_TRIGGER, NOTIFICATION_SUBSCRIPTION_MANAGER_ROLE, NOTIFICATION_UPDATE_ROLE, NOTIFICATION_VIEW_ROLE, OWNER_ROLE, TRIGGER_MANAGER_ROLE, TRIGGER_UPDATE_ROLE, TRIGGER_VIEW_ROLE, UPDATE_NOTIFICATION, UPDATE_TRIGGER, VIEW_NOTIFICATION, VIEW_TRIGGER, ZEN_ADD, ZEN_ADMINISTRATORS_EDIT, ZEN_ADMINISTRATORS_VIEW, ZEN_ADMIN_DEVICE, ZEN_CHANGE_ADMIN_OBJECTS, ZEN_CHANGE_ALERTING_RULES, ZEN_CHANGE_DEVICE, ZEN_CHANGE_DEVICE_PRODSTATE, ZEN_CHANGE_EVENT_VIEWS, ZEN_CHANGE_SETTINGS, ZEN_COMMON, ZEN_DEFINE_COMMANDS_EDIT, ZEN_DEFINE_COMMANDS_VIEW, ZEN_DELETE, ZEN_DELETE_DEVICE, ZEN_EDIT_LOCAL_TEMPLATES, ZEN_EDIT_USER, ZEN_EDIT_USERGROUP, ZEN_MAINTENANCE_WINDOW_EDIT, ZEN_MAINTENANCE_WINDOW_VIEW, ZEN_MANAGER_ROLE, ZEN_MANAGE_DEVICE, ZEN_MANAGE_DEVICE_STATUS, ZEN_MANAGE_DMD, ZEN_MANAGE_EVENTMANAGER, ZEN_MANAGE_EVENTS, ZEN_RUN_COMMANDS, ZEN_SEND_EVENTS, ZEN_UPDATE, ZEN_USER_ROLE, ZEN_VIEW, ZEN_VIEW_HISTORY, ZEN_VIEW_MODIFICATIONS, ZEN_ZPROPERTIES_EDIT, ZEN_ZPROPERTIES_VIEW   

class AddGroupManager(Migrate.Step):
    
    version = Migrate.Version(2, 1, 0)
   
    def cutover(self, dmd):
        
        dmd.buildMenus(
            {'Group_list': [
               {  'action': 'dialog_addUserGroup',
                  'description': 'Add New Group...',
                  'id': 'addUserGroup',
                  'isdialog': True,
                  'ordering': 90.1,
                  'permissions': (ZEN_MANAGE_DMD,)},
               {  'action': 'dialog_deleteUserGroups',
                  'description': 'Delete Groups...',
                  'id': 'deleteUserGroups',
                  'isdialog': True,
                  'ordering': 90.0,
                  'permissions': (ZEN_MANAGE_DMD,)},
               {  'action': 'dialog_addUserToGroup',
                  'description': 'Add User...',
                  'id': 'addUserToGroups',
                  'isdialog': True,
                  'ordering': 80.1,
                  'permissions': (ZEN_MANAGE_DMD,)} ],
              'GroupUser_list': [
               {  'action': 'dialog_addUserToAGroup',
                  'description': 'Add User...',
                  'id': 'addUserToAGroup',
                  'isdialog': True,
                  'ordering': 80.1,
                  'permissions': (ZEN_MANAGE_DMD,)},
               {  'action': 'dialog_deleteUsersFromGroup',
                  'description': 'Delete Users...',
                  'id': 'deleteUsersFromGroup',
                  'isdialog': True,
                  'ordering': 80.0,
                  'permissions': (ZEN_MANAGE_DMD,)} ]
        })
        if hasattr(dmd.zenMenus.Group_list.zenMenuItems, 
            'addUserToGroup'):
            dmd.zenMenus.Group_list.manage_deleteZenMenuItem(
                'addUserToGroup')
        if hasattr(dmd.zenMenus.Group_list.zenMenuItems, 
            'deleteUsersFromGroup'):
            dmd.zenMenus.Group_list.manage_deleteZenMenuItem(
                'deleteUsersFromGroup')
        if hasattr(dmd.zenMenus.GroupUser_list.zenMenuItems, 
            'addUserToGroup'):
            dmd.zenMenus.GroupUser_list.manage_deleteZenMenuItem(
                'addUserToGroup')
        self._addGroupManager(dmd.zport)


    GROUP_ID = 'groupManager'

    def _addGroupManager(self, zport):
        acl = zport.acl_users
        if not hasattr(acl, self.GROUP_ID):
            plugins.ZODBGroupManager.addZODBGroupManager(acl, self.GROUP_ID)
        acl.groupManager.manage_activateInterfaces(['IGroupsPlugin',])


AddGroupManager()
