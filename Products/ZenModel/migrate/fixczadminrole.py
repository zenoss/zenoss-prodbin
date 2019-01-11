##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = '''
This migration script fixes wrong settings for some permissions 
which were introduced by czadminrole migration.
'''


import Migrate

from Products.ZenModel.ZenossSecurity import (
    CZ_ADMIN_ROLE,
    ZEN_CHANGE_DEVICE_PRODSTATE,
    ZEN_CHANGE_EVENT_VIEWS,
    ZEN_MANAGE_EVENTS,
    ZEN_VIEW
)

NO_ACQUIRE_PERMS = (ZEN_CHANGE_DEVICE_PRODSTATE,
                    ZEN_CHANGE_EVENT_VIEWS,
                    ZEN_MANAGE_EVENTS,
                    ZEN_VIEW)


class FixCZAdminRole(Migrate.Step):

    version = Migrate.Version(300, 0, 5)


    def cutover(self, dmd):
        zport = dmd.zport

        if CZ_ADMIN_ROLE in dmd.ZenUsers.getAllRoles():
            for perm in zport.permission_settings():
                if perm['name'] in NO_ACQUIRE_PERMS and perm['acquire'] == 'CHECKED': 
                    roles = [entry['name']
                            for entry in zport.rolesOfPermission(perm['name'])
                            if entry['selected']]

                    zport.manage_permission(perm['name'], roles + [CZ_ADMIN_ROLE], 0)

FixCZAdminRole()
