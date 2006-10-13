#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__='''
This migration script converts Zenoss instances from using old-style,
non-pluggable acl_users "User Folders" to an acl_users based on the
"PluggableAuthenticationService."

Old users, passwords and roles are migrated to PAS with this script.
''' 

__version__ = "$Revision$"[11:-2]

import os

from OFS.Folder import Folder
from Products.PluggableAuthService import plugins
from Products.PluggableAuthService import PluggableAuthService

from Products.ZenModel import refreshLoginForm

import Migrate

class MigrateToPAS(Migrate.Step):
    version = 23.0

    def backupAndCreate(self, context):
        # archive the old "User Folder"
        backupFolder = Folder('backup_acl_users')
        backupFolder._setObject('acl_users', context.acl_users)
        context._setObject(backupFolder.getId(), backupFolder)
        context._delObject('acl_users')

        # create a new PAS acl_users
        PluggableAuthService.addPluggableAuthService(context)
        context.acl_users.title = 'PAS'

        # set up some convenience vars
        orig = context.backup_acl_users.acl_users
        acl = context.acl_users
        dmd = context.getPhysicalRoot().zport.dmd

        # setup the plugins we will need
        plugins.CookieAuthHelper.addCookieAuthHelper(acl, 'cookieAuthHelper')
        plugins.HTTPBasicAuthHelper.addHTTPBasicAuthHelper(
            acl, 'basicAuthHelper')
        plugins.ZODBRoleManager.addZODBRoleManager(acl, 'roleManager')
        plugins.ZODBUserManager.addZODBUserManager(acl, 'userManager')

        # activate the plugins for the interfaces each will be responsible for;
        # note that we are only enabling CookieAuth for the Zenoss portal
        # acl_users, not for the root acl_users.
        physPath = '/'.join(context.getPhysicalPath())
        if physPath == '':
            interfaces = ['IExtractionPlugin']
        elif physPath == '/zport':
            interfaces = ['IExtractionPlugin', 'IChallengePlugin',
                'ICredentialsUpdatePlugin', 'ICredentialsResetPlugin']
        acl.cookieAuthHelper.manage_activateInterfaces(interfaces)
        acl.roleManager.manage_activateInterfaces(['IRolesPlugin',
            'IRoleEnumerationPlugin', 'IRoleAssignerPlugin'])
        acl.userManager.manage_activateInterfaces(['IAuthenticationPlugin',
            'IUserEnumerationPlugin', 'IUserAdderPlugin'])

        # migrate the old user information over to the PAS
        for u in orig.getUsers():
            user, password, domains, roles = (u.name, u.__, u.domains, u.roles)
            acl.userManager.addUser(user, user, password)
            for role in roles:
                acl.roleManager.assignRoleToPrincipal(role, user)
            # initialize UserSettings for each user
            dmd.ZenUsers.getUserSettings(user)

    def cutover(self, dmd):
        newModule = 'Products.PluggableAuthService.PluggableAuthService'
        app = dmd.getPhysicalRoot()
        portal = app.zport
        for context in [app, portal]:
            if context.acl_users.__module__ != newModule:
                self.backupAndCreate(context)
            refreshLoginForm(context.acl_users)

MigrateToPAS()

