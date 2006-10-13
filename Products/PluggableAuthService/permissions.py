##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
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
""" Product-specifict permissions.

$Id: permissions.py 39144 2004-08-12 15:15:55Z jens $
"""
from AccessControl import ModuleSecurityInfo
from AccessControl import Permissions
from AccessControl.Permission import _registeredPermissions
from AccessControl.Permission import pname
from Globals import ApplicationDefaultPermissions
import Products

security = ModuleSecurityInfo( 'Products.PluggableAuthService.permissions' )

security.declarePublic( 'ManageUsers' )
ManageUsers = Permissions.manage_users

security.declarePublic( 'ManageGroups' )
ManageGroups = "Manage Groups"

security.declarePrivate( 'setDefaultRoles' )
def setDefaultRoles( permission, roles ):

    """ Set the defaults roles for a permission.

    o XXX This ought to be in AccessControl.SecurityInfo.
    """
    registered = _registeredPermissions

    if not registered.has_key( permission ):

        registered[ permission ] = 1
        Products.__ac_permissions__=( Products.__ac_permissions__
                                    + ( ( permission, (), roles ), )
                                    )

        mangled = pname(permission)
        setattr(ApplicationDefaultPermissions, mangled, roles)

security.declarePublic( 'SearchPrincipals' )
SearchPrincipals = 'Search for principals'
setDefaultRoles( SearchPrincipals, ( 'Manager', ) )

security.declarePublic( 'SetOwnPassword' )
SetOwnPassword = 'Set own password'
setDefaultRoles( SetOwnPassword, ( 'Authenticated', ) )
