##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = '''
This migration script adds the ZEN_MANAGE_GROUPS permission.
'''


import Migrate


from Products.ZenModel.ZenossSecurity import (
    ZEN_MANAGER_ROLE,
    MANAGER_ROLE,
    CZ_ADMIN_ROLE,
    OWNER_ROLE,
    ZEN_MANAGE_GROUPS,
)


class AddZenManageGroupsPermission(Migrate.Step):

    version = Migrate.Version(300, 0, 6)

    def addPermissions(self, obj, permission, roles=None, acquire=0):
        if not roles:
            roles = []
        if permission not in obj.possible_permissions():
            obj.__ac_permissions__ = (
                obj.__ac_permissions__+((permission, (), roles),))

        for permissionDir in obj.rolesOfPermission(permission):
            if permissionDir['selected']:
                if permissionDir['name'] not in roles:
                    roles.append(permissionDir['name'])
        obj.manage_permission(permission, roles, acquire)

    def cutover(self, dmd):
        zport = dmd.zport
        
        # Add the ZEN_MANAGE_GROUPS permissions on the "manager" roles
        self.addPermissions(zport, ZEN_MANAGE_GROUPS, 
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE, ZEN_MANAGER_ROLE], 1)

        # Restrict the user group management menu
        for item in dmd.zenMenus.Group_list.zenMenuItems():
            item.permissions = (ZEN_MANAGE_GROUPS, ZEN_MANAGE_GROUPS)

AddZenManageGroupsPermission()
