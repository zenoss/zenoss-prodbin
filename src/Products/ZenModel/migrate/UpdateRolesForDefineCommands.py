##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = '''
This migration script puts CZ_ADMIN_ROLE and ZEN_MANAGER_ROLE roles to the ZEN_DEFINE_COMMANDS_EDIT permission.
'''


import Migrate

from Products.ZenModel.ZenossSecurity import (
    CZ_ADMIN_ROLE,
    MANAGER_ROLE,
    ZEN_MANAGER_ROLE,
    ZEN_DEFINE_COMMANDS_EDIT
)
from Products.ZenModel.migrate.UpdateDefineCommandsEditPermission import UpdateDefineCommandsEditPermission


class UpdateRolesForDefineCommands(Migrate.Step):

    version = Migrate.Version(300, 0, 13)

    def cutover(self, dmd):
        zport = dmd.zport
        UpdateDefineCommandsEditPermission.addPermissions.__func__(self, zport, ZEN_DEFINE_COMMANDS_EDIT,
            [MANAGER_ROLE, CZ_ADMIN_ROLE, ZEN_MANAGER_ROLE], 1)


UpdateRolesForDefineCommands()
