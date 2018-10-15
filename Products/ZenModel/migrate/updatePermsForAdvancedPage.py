##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
__doc__ = '''
Update permissions for ZEN_MANAGER for Advanced -> Events and User Interface pages.
'''
import Migrate

from Products.ZenModel.ZenossSecurity import (
    MANAGER_ROLE,
    ZEN_MANAGER_ROLE,
    CZ_ADMIN_ROLE,
    OWNER_ROLE,
    ZEN_MANAGE_UI_SETTINGS,
    ZEN_MANAGE_EVENT_CONFIG,
)
from Products.ZenModel.ZMigrateVersion import SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION


class UpdatePermsForAdvancedPage(Migrate.Step):

    version = Migrate.Version(SCHEMA_MAJOR, SCHEMA_MINOR, SCHEMA_REVISION)

    def addPermissions(self, obj, permission, roles=None, acquire=0):
        if not roles:
            roles = []
        if permission not in obj.possible_permissions():
            obj.__ac_permissions__ = (
                    obj.__ac_permissions__ + ((permission, (), roles),))
        for permissionDir in obj.rolesOfPermission(permission):
            if permissionDir['selected']:
                if permissionDir['name'] not in roles:
                    roles.append(permissionDir['name'])
        obj.manage_permission(permission, roles, acquire)


    def cutover(self, dmd):

        zport = dmd.zport

        # update permission to see UI settings page for ZEN_MANAGER.
        self.addPermissions(zport, ZEN_MANAGE_UI_SETTINGS,
                            [OWNER_ROLE, MANAGER_ROLE, ZEN_MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # update permission to see Event configuration  page for ZEN_MANAGER.
        self.addPermissions(zport,  ZEN_MANAGE_EVENT_CONFIG,
                            [OWNER_ROLE, MANAGER_ROLE, ZEN_MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

UpdatePermsForAdvancedPage()
