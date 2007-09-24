###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate
import Globals
from Products.PluggableAuthService import plugins
from Products.ZenModel.ZenossSecurity import *   

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
               
        self._addGroupManager(dmd.zport)


    GROUP_ID = 'groupManager'

    def _addGroupManager(self, zport):
        acl = zport.acl_users
        if not hasattr(acl, self.GROUP_ID):
            plugins.ZODBGroupManager.addZODBGroupManager(acl, self.GROUP_ID)
        acl.groupManager.manage_activateInterfaces(['IGroupsPlugin',])


AddGroupManager()
