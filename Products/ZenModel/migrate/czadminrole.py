##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = '''
This migration script adds the CZAdmin role.
'''


import Migrate

from Products.ZenModel.ZenossSecurity import (
    ZEN_MANAGER_ROLE,
    MANAGER_ROLE,
    CZ_ADMIN_ROLE,
    OWNER_ROLE,
    ZEN_MANAGE_GLOBAL_SETTINGS,
    ZEN_MANAGE_GLOBAL_COMMANDS,
    ZEN_MANAGE_CONTROL_CENTER,
    ZEN_EDIT_USER,
    ZEN_MANAGE_USERS,
    ZEN_VIEW_USERS,
    ZEN_MANAGE_ZENPACKS,
    ZEN_VIEW_SOFTWARE_VERSIONS,
    ZEN_MANAGE_EVENT_CONFIG,
    ZEN_MANAGE_UI_SETTINGS,
    ZEN_MANAGE_LDAP_SETTINGS,
    ZEN_VIEW_LICENSING,
    ZEN_MANAGE_SUPPORT_BUNDLES,
)


class CZAdminRole(Migrate.Step):

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
        if CZ_ADMIN_ROLE not in zport.__ac_roles__:
            zport.__ac_roles__ += (CZ_ADMIN_ROLE,)
        rms = (dmd.getPhysicalRoot().acl_users.roleManager,
               zport.acl_users.roleManager)
        for rm in rms:
            if CZ_ADMIN_ROLE not in rm.listRoleIds():
                rm.addRole(CZ_ADMIN_ROLE)

        # Give CZAdmin everything ZenManager has
        for perm in zport.possible_permissions():
            roles = [entry['name']
                     for entry in zport.rolesOfPermission(perm)
                     if entry['selected']]
            if ZEN_MANAGER_ROLE in roles:
                zport.manage_permission(perm, roles + [CZ_ADMIN_ROLE], 1)

        # SETTINGS #

        # Add "Manage Global Settings" perm to CZAdmin
        self.addPermissions(zport, ZEN_MANAGE_GLOBAL_SETTINGS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # COMMANDS #

        # Add "Manage Global Commands" perm to CZAdmin and ZenManager
        self.addPermissions(zport, ZEN_MANAGE_GLOBAL_COMMANDS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE,
                             ZEN_MANAGER_ROLE], 1)

        # USERS #

        # Remove "Edit Users" perm from ZenManager
        self.addPermissions(zport, ZEN_EDIT_USER,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # Add "View Users" perm to CZAdmin, Manager and ZenManager
        self.addPermissions(zport, ZEN_VIEW_USERS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE,
                             ZEN_MANAGER_ROLE], 1)

        # Add "Manage Users" perm to CZAdmin and Manager
        self.addPermissions(zport, ZEN_MANAGE_USERS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # Restrict the user management menu
        for item in dmd.zenMenus.User_list.zenMenuItems():
            item.permissions = (ZEN_MANAGE_USERS,)

        # Restrict the user group management menu
        for item in dmd.zenMenus.Group_list.zenMenuItems():
            item.permissions = (ZEN_MANAGE_USERS,)

        # CONTROL CENTER #

        # Add "Manage Control Center" perm to CZAdmin
        self.addPermissions(zport, ZEN_MANAGE_CONTROL_CENTER,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # ZENPACKS #

        # Add "Manage ZenPacks" perm to CZAdmin and ZenManager
        self.addPermissions(zport, ZEN_MANAGE_ZENPACKS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE,
                             ZEN_MANAGER_ROLE], 1)

        # VERSIONS #

        # Add "View Software Versions" perm to CZAdmin and Manager
        self.addPermissions(zport, ZEN_VIEW_SOFTWARE_VERSIONS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # EVENTS #

        # Add "Manage Event Configuration" perm to CZAdmin and Manager
        self.addPermissions(zport, ZEN_MANAGE_EVENT_CONFIG,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # UI SETTINGS #

        # Add "Manage UI Settings" perm to CZAdmin and Manager
        self.addPermissions(zport, ZEN_MANAGE_UI_SETTINGS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # LDAP SETTINGS #

        # Add "Manage LDAP Settings" perm to CZAdmin and Manager
        # Note: This permission isn't used in Core, only in the
        # LDAPAuthenticator pack
        self.addPermissions(zport, ZEN_MANAGE_LDAP_SETTINGS,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # LICENSING SETTINGS #

        # Add "View Licensing" perm to CZAdmin and Manager
        # Note: This permission isn't used in Core, only in the
        # Licensing pack
        self.addPermissions(zport, ZEN_VIEW_LICENSING,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)

        # SUPPORTBUNDLE SETTINGS #

        # Add "Manage Support Bundles" perm to CZAdmin and Manager
        # Note: This permission isn't used in Core, only in the
        # Licensing pack
        self.addPermissions(zport, ZEN_MANAGE_SUPPORT_BUNDLES,
                            [OWNER_ROLE, MANAGER_ROLE, CZ_ADMIN_ROLE], 1)



CZAdminRole()
