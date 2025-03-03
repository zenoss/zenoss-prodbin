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
import logging

from Products.Zuul.catalog.model_catalog_init import reindex_model_catalog
from Products.Zuul.catalog.indexable import DeviceIndexable


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

log = logging.getLogger("zen.migrate")

class FixCZAdminRole(Migrate.Step):

    version = Migrate.Version(300, 0, 6)

    def cutover(self, dmd):
        zport = dmd.zport
        requires_reindex = False

        if CZ_ADMIN_ROLE in dmd.ZenUsers.getAllRoles():
            for perm in zport.permission_settings():
                if perm['name'] in NO_ACQUIRE_PERMS and perm['acquire'] == 'CHECKED':
                    roles = [entry['name']
                            for entry in zport.rolesOfPermission(perm['name'])
                            if entry['selected']]

                    zport.manage_permission(perm['name'], roles + [CZ_ADMIN_ROLE], 0)
                    requires_reindex = True

            if requires_reindex:
                log.info("Performing reindexing due to permission updates, this can take a while.")
                reindex_model_catalog(dmd,
                                      root="/zport/dmd/Devices",
                                      idxs=("allowedRolesAndUsers",),
                                      types=DeviceIndexable)


FixCZAdminRole()
