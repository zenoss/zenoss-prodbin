##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################

from Testing import ZopeTestCase

ZopeTestCase.installProduct('PluginRegistry')
ZopeTestCase.installProduct('PluggableAuthService')
ZopeTestCase.installProduct('StandardCacheManagers')
ZopeTestCase.installProduct('GenericSetup')

from Testing.ZopeTestCase import user_name
from Testing.ZopeTestCase import user_password
from Testing.ZopeTestCase import user_role

from base64 import encodestring
user_auth = encodestring('%s:%s' % (user_name, user_password)).rstrip()

from Products.PluggableAuthService.interfaces.plugins import \
    IAuthenticationPlugin, IUserEnumerationPlugin, IRolesPlugin, \
    IRoleEnumerationPlugin, IRoleAssignerPlugin, \
    IChallengePlugin, IExtractionPlugin, IUserAdderPlugin


class PASTestCase(ZopeTestCase.ZopeTestCase):
    """ZopeTestCase with a PAS instead of the default user folder
    """

    def _setupUserFolder(self):
        """Creates a Pluggable Auth Service."""
        factory = self.folder.manage_addProduct['PluggableAuthService']
        factory.addPluggableAuthService()
        pas = self.folder.acl_users
        factory = pas.manage_addProduct['PluggableAuthService']
        factory.addHTTPBasicAuthHelper('http_auth')
        factory.addZODBUserManager('users')
        factory.addZODBRoleManager('roles')
        plugins = pas.plugins
        plugins.activatePlugin(IChallengePlugin, 'http_auth')
        plugins.activatePlugin(IExtractionPlugin, 'http_auth')
        plugins.activatePlugin(IUserAdderPlugin, 'users')
        plugins.activatePlugin(IAuthenticationPlugin, 'users')
        plugins.activatePlugin(IUserEnumerationPlugin, 'users')
        plugins.activatePlugin(IRolesPlugin, 'roles')
        plugins.activatePlugin(IRoleAssignerPlugin, 'roles')
        plugins.activatePlugin(IRoleEnumerationPlugin, 'roles')

    def _setupUser(self):
        """Creates the default user."""
        # OMFG, why doesn't PAS support userFolderAddUser?
        uf = self.folder.acl_users
        uf._doAddUser(user_name, user_password, [user_role], [])

