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
""" Classes:  PropertiedUser

$Id: PropertiedUser.py 67083 2006-04-18 21:56:22Z jens $
"""

from Acquisition import aq_inner, aq_parent
from AccessControl.User import BasicUser
from AccessControl.PermissionRole import _what_not_even_god_should_do

from interfaces.authservice import IPropertiedUser
from UserPropertySheet import UserPropertySheet
from utils import classImplements

class PropertiedUser( BasicUser ):

    """ User objects which manage propertysheets, obtained from decorators.
    """
    def __init__( self, id, login=None ):

        self._id = id

        if login is None:
            login = id

        self._login = login

        self._propertysheets = {}   # *Not* persistent!
        self._groups = {}
        self._roles = {}


    #
    #   BasicUser's public interface
    #
    def getId( self ):

        """ -> user ID
        """
        return self._id

    def getUserName( self ):

        """ -> login name
        """
        return self._login

    def getRoles( self ):

        """ -> [ role ]

        o Include only "global" roles.
        """
        return self._roles.keys()

    def getGroups(self):
        """ -> [group]

        o Return the groups the user is in.
        """
        return self._groups.keys()

    def getDomains( self ):

        """ -> [ domain ]

        o The list represents the only domains from which the user is
          allowed to access the system.
        """
        return ()

    def getRolesInContext( self, object ):

        """ Return the list of roles assigned to the user.

        o Include local roles assigned in context of the passed-in object.

        o Include *both* local roles assigned directly to us *and* those
          assigned to our groups.

        o Ripped off from AccessControl.User.BasicUser, which provides
          no other extension mechanism. :(
        """
        user_id = self.getId()
        # [ x.getId() for x in self.getGroups() ]
        group_ids = self.getGroups()

        principal_ids = list( group_ids )
        principal_ids.insert( 0, user_id )

        local ={} 
        object = aq_inner( object )

        while 1:

            local_roles = getattr( object, '__ac_local_roles__', None )

            if local_roles:

                if callable( local_roles ):
                    local_roles = local_roles()

                dict = local_roles or {}

                for principal_id in principal_ids:
                    for role in dict.get( principal_id, [] ):
                        local[ role ] = 1

            inner = aq_inner( object )
            parent = aq_parent( inner )

            if parent is not None:
                object = parent
                continue

            new = getattr( object, 'im_self', None )

            if new is not None:

                object = aq_inner( new )
                continue

            break

        return list( self.getRoles() ) + local.keys()

    def allowed( self, object, object_roles=None ):

        """ Check whether the user has access to object.

        o The user must have one of the roles in object_roles to allow access.

        o Include *both* local roles assigned directly to us *and* those
          assigned to our groups.

        o Ripped off from AccessControl.User.BasicUser, which provides
          no other extension mechanism. :(
        """
        if object_roles is _what_not_even_god_should_do:
            return 0

        # Short-circuit the common case of anonymous access.
        if object_roles is None or 'Anonymous' in object_roles:
            return 1

        # Provide short-cut access if object is protected by 'Authenticated'
        # role and user is not nobody
        if 'Authenticated' in object_roles and (
            self.getUserName() != 'Anonymous User'):
            return 1

        # Check for ancient role data up front, convert if found.
        # This should almost never happen, and should probably be
        # deprecated at some point.
        if 'Shared' in object_roles:
            object_roles = self._shared_roles(object)
            if object_roles is None or 'Anonymous' in object_roles:
                return 1

        # Check for a role match with the normal roles given to
        # the user, then with local roles only if necessary. We
        # want to avoid as much overhead as possible.
        user_roles = self.getRoles()
        for role in object_roles:
            if role in user_roles:
                if self._check_context(object):
                    return 1
                return None

        # Still have not found a match, so check local roles. We do
        # this manually rather than call getRolesInContext so that
        # we can incur only the overhead required to find a match.
        inner_obj = aq_inner( object )
        user_id = self.getId()
        # [ x.getId() for x in self.getGroups() ]
        group_ids = self.getGroups()

        principal_ids = list( group_ids )
        principal_ids.insert( 0, user_id )

        while 1:

            local_roles = getattr( inner_obj, '__ac_local_roles__', None )

            if local_roles:

                if callable( local_roles ):
                    local_roles = local_roles()

                dict = local_roles or {}

                for principal_id in principal_ids:

                    local_roles = dict.get( principal_id, [] )

                    for role in object_roles:

                        if role in local_roles:

                            if self._check_context( object ):
                                return 1

                            return 0

            inner = aq_inner( inner_obj )
            parent = aq_parent( inner )

            if parent is not None:
                inner_obj = parent
                continue

            new = getattr( inner_obj, 'im_self', None )

            if new is not None:
                inner_obj = aq_inner( new )
                continue

            break

        return None

    #
    #   Interfaces to allow user folder plugins to annotate the user.
    #
    def _addGroups( self, groups=() ):

        """ Extend our set of groups.

        o Don't complain about duplicates.
        """
        for group in groups:
            self._groups[ group ] = 1

    def _addRoles( self, roles=() ):

        """ Extend our set of roles.

        o Don't complain about duplicates.
        """
        for role in roles:
            self._roles[ role ] = 1


    #
    #   Propertysheet management
    #
    def listPropertysheets( self ):

        """ -> [ propertysheet_id ]
        """
        return self._propertysheets.keys()

    def getPropertysheet( self, id ):

        """ id -> sheet

        o Raise KeyError if no such seet exists.
        """
        return self._propertysheets[ id ]

    __getitem__ = getPropertysheet

    def addPropertysheet( self, id, data ):

        """ Add a new propertysheet.

        o Raise KeyError if a sheet of the given ID already exists.
        """
        if self._propertysheets.get( id ) is not None:
            raise KeyError, "Duplicate property sheet: %s" % id

        self._propertysheets[ id ] = UserPropertySheet( id, **data )


classImplements( PropertiedUser,
                 IPropertiedUser )
