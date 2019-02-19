##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = '''
This migration script puts CZ_ADMIN_ROLE role to the ZEN_DEFINE_COMMANDS_EDIT permission.
'''


import Migrate

from Products.ZenModel.ZenossSecurity import (
    CZ_ADMIN_ROLE,
    MANAGER_ROLE,
    ZEN_DEFINE_COMMANDS_EDIT
)

class UpdateDefineCommandsEditPermission(Migrate.Step):

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

        # Put CZ_ADMIN_ROLE to ZEN_DEFINE_COMMANDS_EDIT permission ZEN-30566.
        self.addPermissions(zport, ZEN_DEFINE_COMMANDS_EDIT,
            [MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

UpdateDefineCommandsEditPermission()
