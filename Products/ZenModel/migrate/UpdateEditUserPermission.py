##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = '''
This migration script puts back ZEN_MANAGER role to the ZEN_EDIT_USER permission.
'''


import Migrate

from Products.ZenModel.ZenossSecurity import (
    ZEN_MANAGER_ROLE,
    MANAGER_ROLE,
    CZ_ADMIN_ROLE,
    OWNER_ROLE,
    ZEN_EDIT_USER
)


class UpdateEditUserPermission(Migrate.Step):
    
    version = Migrate.Version(300, 0, 0)

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

        # Put back ZenManager to ZEN_EDIT_USER permission ZEN-30684.
        self.addPermissions(zport, ZEN_EDIT_USER,
            [OWNER_ROLE, MANAGER_ROLE, ZEN_MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

UpdateEditUserPermission()
