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
        
from Products.PluggableAuthService import plugins
from Products.PluggableAuthService import PluggableAuthService

class MigrateToPAS(Migrate.Step):
    version = 23.0

    def cutover(self, dmd):
        # archive the old "User Folder"
        app = dmd.getPhysicalRoot()
        backup = app.zport.acl_users._getCopy(app.zport.acl_users)
        setattr(app.zport, 'acl_users_orig', backup)
        newObs = [ x for x in app.zport._objects if x['id'] != 'acl_users'] + \
            [{'meta_type': 'User Folder', 'id': 'acl_users_orig'}]
        app.zport._objects = tuple(newObs)
        # create a new PAS acl_users
        PluggableAuthService.addPluggableAuthService(app.zport)
        # set up some convenience vars
        orig = app.zport.acl_users_orig
        acl = app.zport.acl_users

        # setup the plugins we will need
        plugins.CookieAuthHelper.addCookieAuthHelper(acl, 'cookieAuthHelper')
        plugins.HTTPBasicAuthHelper.addHTTPBasicAuthHelper(acl, 'basicAuthHelper')
        plugins.ZODBRoleManager.addZODBRoleManager(acl, 'roleManager')
        plugins.ZODBUserManager.addZODBUserManager(acl, 'userManager')

        # activate the plugins for interfaces each will be responsible for
        acl.cookieAuthHelper.manage_activateInterfaces(['IExtractionPlugin',
            'IChallengePlugin', 'ICredentialsUpdatePlugin',
            'ICredentialsResetPlugin'])
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

MigrateToPAS()

