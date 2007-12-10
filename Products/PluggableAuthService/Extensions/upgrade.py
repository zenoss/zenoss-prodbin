##############################################################################
#
# Copyright (c) 2004 Zope Corporation. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Visible Source 
# License, Version 1.0 (ZVSL).  A copy of the ZVSL should accompany this 
# distribution.
#
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" External method for upgrading existing AccessControl.User.UserFolder

    NOTA BENE: Use at your own risk. This external method will replace a
    stock User Folder (AccessControl.User.UserFolder) with a
    PluggableAuthService consisting of the following:

        - ZODBUserManager with a record for each existing User
          (AccessControl.User.User)

        - ZODBRoleManger with a record for each existing role present
          in the __ac_roles__ attribute of the container (minus Anonymous
          and Authenticated)

    Each migrated user will be assigned the global roles they have in the
    previous acl_users record.

$Id: upgrade.py 65465 2006-02-25 20:01:13Z jens $
"""
import logging

try:
    import transaction
    get_transaction = transaction.get
except ImportError:
    # Zope 2.7 backwards compatibility
    pass

def _write(response, tool, message):
    logger = logging.getLogger('PluggableAuthService.upgrade.%s' % tool)
    logger.info(message)
    if response is not None:
        response.write(message)

def _replaceUserFolder(self, RESPONSE=None):
    """replaces the old acl_users folder with a PluggableAuthService,
    preserving users and passwords, if possible
    """
    from Acquisition import aq_base
    from Products.PluggableAuthService.PluggableAuthService \
        import PluggableAuthService, _PLUGIN_TYPE_INFO
    from Products.PluginRegistry.PluginRegistry import PluginRegistry
    from Products.PluggableAuthService.plugins.ZODBUserManager \
        import ZODBUserManager
    from Products.PluggableAuthService.plugins.ZODBRoleManager \
        import ZODBRoleManager
    from Products.PluggableAuthService.interfaces.plugins \
         import IAuthenticationPlugin, IUserEnumerationPlugin
    from Products.PluggableAuthService.interfaces.plugins \
        import IRolesPlugin, IRoleEnumerationPlugin, IRoleAssignerPlugin

    if getattr( aq_base(self), '__allow_groups__', None ):
        if self.__allow_groups__.__class__ is PluggableAuthService:
            _write( RESPONSE
                  , 'replaceUserFolder'
                  , 'Already replaced this user folder\n' )
            return

        # Capture all the user info from the previous user folder,
        # then delete it.
        old_acl = self.__allow_groups__
        user_map = []
        for user_name in old_acl.getUserNames():
            old_user = old_acl.getUser( user_name )
            _write( RESPONSE
                  , 'replaceRootUserFolder'
                  , 'Capturing user info for %s\n' % user_name )
            user_map.append(
                { 'login' : user_name,
                  'password' : old_user._getPassword(),
                  'roles' : old_user.getRoles() }
                )
        self._delObject( 'acl_users' )

        # Create the new PluggableAuthService, and re-populate from
        # the captured data
        _pas = self.manage_addProduct['PluggableAuthService']
        new_pas = _pas.addPluggableAuthService()
        new_acl = self.acl_users

        user_folder = ZODBUserManager( 'users' )
        new_acl._setObject( 'users', user_folder )
        role_manager = ZODBRoleManager( 'roles' )
        new_acl._setObject( 'roles', role_manager )

        plugins = getattr( new_acl, 'plugins' )
        plugins.activatePlugin( IAuthenticationPlugin, 'users' )
        plugins.activatePlugin( IUserEnumerationPlugin, 'users' )
        plugins.activatePlugin( IRolesPlugin, 'roles' )
        plugins.activatePlugin( IRoleEnumerationPlugin, 'roles' )
        plugins.activatePlugin( IRoleAssignerPlugin, 'roles' )
        for user_dict in user_map:
            _write( RESPONSE
                  , 'replaceRootUserFolder'
                  , 'Translating user %s\n' % user_name )
            login = user_dict['login']
            password = user_dict['password']
            roles = user_dict['roles']

            _migrate_user( new_acl, login, password, roles )
        _write( RESPONSE
              , 'replaceRootUserFolder'
              , 'Replaced root acl_users with PluggableAuthService\n' )

    get_transaction().commit()

def _migrate_user( pas, login, password, roles ):

    from AccessControl import AuthEncoding

    if AuthEncoding.is_encrypted( password ):
        pas.users._user_passwords[ login ] = password
        pas.users._login_to_userid[ login ] = login
        pas.users._userid_to_login[ login ] = login
    else:
        pas.users.addUser( login, login, password )

    new_user = pas.getUser( login )
    for role_id in roles:
        if role_id not in ['Authenticated', 'Anonymous']:
            pas.roles.assignRoleToPrincipal( role_id,
                                             new_user.getId() )

def _upgradeLocalRoleAssignments(self, RESPONSE=None):
    """ upgrades the __ac_local_roles__ attributes on objects to account
        for a move to using the PluggableAuthService.
    """
    from Acquisition import aq_base

    seen = {}

    def descend(user_folder, obj):
        path = obj.getPhysicalPath()
        if path not in seen:
            # get __ac_local_roles__, break it apart and refashion it
            # with new spellings.
            seen[path] = 1
            if getattr( aq_base( obj ), '__ac_local_roles__', None ):
                if not callable(obj.__ac_local_roles__):
                    new_map = {}
                    map = obj.__ac_local_roles__
                    for key in map.keys():
                        new_principals = user_folder.searchPrincipals(id=key)
                        if not new_principals:
                            _write(
                                RESPONSE
                              , 'upgradeLocalRoleAssignmentsFromRoot'
                              , '  Ignoring map for unknown principal %s\n'
                                % key )
                            new_map[key] = map[key]
                            continue
                        npid = new_principals[0]['id']
                        new_map[npid] = map[key]
                        _write( RESPONSE
                              , 'upgradeLocalRoleAssignmentsFromRoot'
                              , '  Translated %s to %s\n' % ( key, npid ) )
                        _write( RESPONSE
                              , 'upgradeLocalRoleAssignmentsFromRoot'
                              , '  Assigned roles %s to %s\n' % ( map[key]
                                                                , npid ) )
                    obj.__ac_local_roles__ = new_map
                    _write( RESPONSE
                          , 'upgradeLocalRoleAssignmentsFromRoot'
                          , ( 'Local Roles map changed for (%s)\n'
                              % '/'.join(path) ) )
            if (len(seen) % 100 ) == 0:
                get_transaction().commit()
                _write( RESPONSE
                      , 'upgradeLocalRoleAssignmentsFromRoot'
                      , "  -- committed at object # %d\n" % len( seen ) )
            if getattr(aq_base(obj), 'isPrincipiaFolderish', 0):
                for o in obj.objectValues():
                    descend(user_folder, o)

    if getattr( self, '_upgraded_acl_users', None ):
        _write( RESPONSE
              , '_upgradeLocalRoleAssignments'
              , 'Local role assignments have already been updated.\n' )
        return

    descend(self.acl_users, self)

    get_transaction().commit()

# External Method to use

def replace_acl_users(self, RESPONSE=None):
    _replaceUserFolder(self, RESPONSE)
    _upgradeLocalRoleAssignments(self, RESPONSE)
    self._upgraded_acl_users = 1
    _write( RESPONSE
          , 'replace_acl_users'
          , 'Root acl_users has been replaced,'
            ' and local role assignments updated.\n' )
