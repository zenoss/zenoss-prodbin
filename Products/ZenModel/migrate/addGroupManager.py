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

class AddGroupManager(Migrate.Step):
    
    version = Migrate.Version(2, 1, 0)
   
    def cutover(self, dmd):
        
        dmd.buildMenus(
            {'Group_list': [  {  'action': 'dialog_addToZenPack',
                  'description': 'Add to ZenPack...',
                  'id': 'addToZenPack',
                  'isdialog': True,
                  'ordering': 0.0,
                  'permissions': ('View',)},
               {  'action': 'dialog_addUserGroup',
                  'description': 'Add New Group...',
                  'id': 'addUserGroup',
                  'isdialog': True,
                  'ordering': 90.0,
                  'permissions': ('Manage DMD',)},
               {  'action': 'dialog_deleteUserGroups',
                  'description': 'Delete Groups...',
                  'id': 'deleteUserGroups',
                  'isdialog': True,
                  'ordering': 70.0,
                  'permissions': ('Manage DMD',)},
               {  'action': 'dialog_addUserToGroup',
                  'description': 'Add User...',
                  'id': 'addUserToGroup',
                  'isdialog': True,
                  'ordering': 90.0,
                  'permissions': ('Manage DMD',)},
               {  'action': 'dialog_deleteUsersFromGroup',
                  'description': 'Delete Users...',
                  'id': 'deleteUsersFromGroup',
                  'isdialog': True,
                  'ordering': 70.0,
                  'permissions': ('Manage DMD',) } ] 
                  })     
               
        self._addGroupManager(dmd.zport)


    GROUP_ID = 'groupManager'

    def _addGroupManager(self, zport):
        acl = zport.acl_users
        if not hasattr(acl, self.GROUP_ID):
            plugins.ZODBGroupManager.addZODBGroupManager(acl, self.GROUP_ID)
        acl.groupManager.manage_activateInterfaces(['IGroupsPlugin',])


AddGroupManager()
