##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors. All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Unit test security.

$Id: security.py 41231 2006-01-08 18:01:44Z yuppie $
"""

from AccessControl.PermissionRole import rolesForPermissionOn
from Acquisition import Implicit


class PermissiveSecurityPolicy:
    """
        Very permissive security policy for unit testing purposes.
    """
    #
    #   Standard SecurityPolicy interface
    #
    def validate( self
                , accessed=None
                , container=None
                , name=None
                , value=None
                , context=None
                , roles=None
                , *args
                , **kw):
        if name and name.startswith('hidden'):
            return False
        else:
            return True

    def checkPermission(self, permission, object, context):
        if permission == 'forbidden permission':
            return 0
        roles = rolesForPermissionOn(permission, object)
        if isinstance(roles, basestring):
            roles=[roles]
        return context.user.allowed(object, roles)


class OmnipotentUser( Implicit ):
    """
      Omnipotent User for unit testing purposes.
    """
    def getId( self ):
        return 'all_powerful_Oz'

    getUserName = getId

    def getRoles(self):
        return ('Manager',)

    def allowed( self, object, object_roles=None ):
        return 1

    def getRolesInContext(self, object):
        return ('Manager',)

    def _check_context(self, object):
        return True


class UserWithRoles( Implicit ):
    """
      User with roles specified in constructor
      for unit testing purposes.
    """
    def __init__( self, *roles ):
        self._roles = roles

    def getId( self ):
        return 'high_roller'

    getUserName = getId

    def getRoles(self):
        return self._roles

    def allowed( self, object, object_roles=None ):
        if object_roles is None:
            object_roles=()
        for orole in object_roles:
            if orole in self._roles:
                return 1
        return 0

class AnonymousUser( Implicit ):
    """
      Anonymous USer for unit testing purposes.
    """
    def getId( self ):
        return 'Anonymous User'

    getUserName = getId

    def has_permission(self, permission, obj):
        # For types tool tests dealing with filtered_meta_types
        return 1

    def allowed( self, object, object_roles=None ):
        # for testing permissions on actions
        if object.getId() == 'actions_dummy':
            if 'Anonymous' in object_roles:
                return 1
            else:
                return 0
        return 1

    def getRoles(self):
        return ('Anonymous',)
