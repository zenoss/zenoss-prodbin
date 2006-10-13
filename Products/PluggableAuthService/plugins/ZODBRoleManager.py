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
""" Classes: ZODBRoleManager

$Id: ZODBRoleManager.py 69891 2006-08-30 15:41:06Z andrew $
"""
from Acquisition import aq_parent, aq_inner
from AccessControl import ClassSecurityInfo
from BTrees.OOBTree import OOBTree
from Globals import InitializeClass

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins \
    import IRolesPlugin
from Products.PluggableAuthService.interfaces.plugins \
    import IRoleEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins \
    import IRoleAssignerPlugin

from Products.PluggableAuthService.permissions import ManageUsers
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class IZODBRoleManager(Interface):
    """ Marker interface.
    """

manage_addZODBRoleManagerForm = PageTemplateFile(
    'www/zrAdd', globals(), __name__='manage_addZODBRoleManagerForm' )

def addZODBRoleManager( dispatcher, id, title=None, REQUEST=None ):
    """ Add a ZODBRoleManager to a Pluggable Auth Service. """

    zum = ZODBRoleManager(id, title)
    dispatcher._setObject(zum.getId(), zum)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(
                                '%s/manage_workspace'
                                '?manage_tabs_message='
                                'ZODBRoleManager+added.'
                            % dispatcher.absolute_url())

class ZODBRoleManager( BasePlugin ):

    """ PAS plugin for managing roles in the ZODB.
    """
    meta_type = 'ZODB Role Manager'

    security = ClassSecurityInfo()

    def __init__(self, id, title=None):

        self._id = self.id = id
        self.title = title

        self._roles = OOBTree()
        self._principal_roles = OOBTree()

    def manage_afterAdd( self, item, container ):

        if item is self:
            role_holder = aq_parent( aq_inner( container ) )
            for role in getattr( role_holder, '__ac_roles__', () ):
                try:
                    if role not in ('Anonymous', 'Authenticated'):
                        self.addRole( role )
                except KeyError:
                    pass

        if 'Manager' not in self._roles:
            self.addRole( 'Manager' )

    #
    #   IRolesPlugin implementation
    #
    security.declarePrivate( 'getRolesForPrincipal' )
    def getRolesForPrincipal( self, principal, request=None ):

        """ See IRolesPlugin.
        """
        result = list( self._principal_roles.get( principal.getId(), () ) )

        getGroups = getattr( principal, 'getGroups', lambda x: () )
        for group_id in getGroups():
            result.extend( self._principal_roles.get( group_id, () ) )

        return tuple( result )

    #
    #   IRoleEnumerationPlugin implementation
    #
    def enumerateRoles( self
                      , id=None
                      , exact_match=False
                      , sort_by=None
                      , max_results=None
                      , **kw
                      ):

        """ See IRoleEnumerationPlugin.
        """
        role_info = []
        role_ids = []
        plugin_id = self.getId()

        if isinstance( id, str ):
            id = [ id ]

        if exact_match and ( id ):
            role_ids.extend( id )

        if role_ids:
            role_filter = None

        else:   # Searching
            role_ids = self.listRoleIds()
            role_filter = _ZODBRoleFilter( id, **kw )

        for role_id in role_ids:

            if self._roles.get( role_id ):
                e_url = '%s/manage_roles' % self.getId()
                p_qs = 'role_id=%s' % role_id
                m_qs = 'role_id=%s&assign=1' % role_id

                info = {}
                info.update( self._roles[ role_id ] )

                info[ 'pluginid' ] = plugin_id
                info[ 'properties_url'  ] = '%s?%s' % (e_url, p_qs)
                info[ 'members_url'  ] = '%s?%s' % (e_url, m_qs)

                if not role_filter or role_filter( info ):
                    role_info.append( info )

        return tuple( role_info )

    #
    #   IRoleAssignerPlugin implementation
    #
    security.declarePrivate( 'doAssignRoleToPrincipal' )
    def doAssignRoleToPrincipal( self, principal_id, role ):
        return self.assignRoleToPrincipal( role, principal_id )

    #
    #   Role management API
    #
    security.declareProtected( ManageUsers, 'listRoleIds' )
    def listRoleIds( self ):

        """ Return a list of the role IDs managed by this object.
        """
        return self._roles.keys()

    security.declareProtected( ManageUsers, 'listRoleInfo' )
    def listRoleInfo( self ):

        """ Return a list of the role mappings.
        """
        return self._roles.values()

    security.declareProtected( ManageUsers, 'getRoleInfo' )
    def getRoleInfo( self, role_id ):

        """ Return a role mapping.
        """
        return self._roles[ role_id ]

    security.declareProtected( ManageUsers, 'addRole' )
    def addRole( self, role_id, title='', description='' ):

        """ Add 'role_id' to the list of roles managed by this object.

        o Raise KeyError on duplicate.
        """
        if self._roles.get( role_id ) is not None:
            raise KeyError, 'Duplicate role: %s' % role_id

        self._roles[ role_id ] = { 'id' : role_id
                                 , 'title' : title
                                 , 'description' : description
                                 }

    security.declareProtected( ManageUsers, 'updateRole' )
    def updateRole( self, role_id, title, description ):

        """ Update title and description for the role.

        o Raise KeyError if not found.
        """
        self._roles[ role_id ].update( { 'title' : title
                                       , 'description' : description
                                       } )

    security.declareProtected( ManageUsers, 'removeRole' )
    def removeRole( self, role_id ):

        """ Remove 'role_id' from the list of roles managed by this object.

        o Raise KeyError if not found.
        """
        for principal_id in self._principal_roles.keys():
            self.removeRoleFromPrincipal( role_id, principal_id )

        del self._roles[ role_id ]

    #
    #   Role assignment API
    #
    security.declareProtected( ManageUsers, 'listAvailablePrincipals' )
    def listAvailablePrincipals( self, role_id, search_id ):

        """ Return a list of principal IDs to whom a role can be assigned.

        o If supplied, 'search_id' constrains the principal IDs;  if not,
          return empty list.

        o Omit principals with existing assignments.
        """
        result = []

        if search_id:  # don't bother searching if no criteria

            parent = aq_parent( self )

            for info in parent.searchPrincipals( max_results=20
                                               , sort_by='id'
                                               , id=search_id
                                               , exact_match=False
                                               ):
                id = info[ 'id' ]
                title = info.get( 'title', id )
                if ( role_id not in self._principal_roles.get( id, () )
                 and role_id != id ):
                    result.append( ( id, title ) )

        return result

    security.declareProtected( ManageUsers, 'listAssignedPrincipals' )
    def listAssignedPrincipals( self, role_id ):

        """ Return a list of principal IDs to whom a role is assigned.
        """
        result = []

        for k, v in self._principal_roles.items():
            if role_id in v:
                # should be at most one and only one mapping to 'k'

                parent = aq_parent( self )
                info = parent.searchPrincipals( id=k, exact_match=True )
                assert( len( info ) in ( 0, 1 ) )
                if len( info ) == 0:
                    title = '<%s: not found>' % k
                else:
                    title = info[0].get( 'title', k )
                result.append( ( k, title ) )

        return result

    security.declareProtected( ManageUsers, 'assignRoleToPrincipal' )
    def assignRoleToPrincipal( self, role_id, principal_id ):

        """ Assign a role to a principal (user or group).

        o Return a boolean indicating whether a new assignment was created.

        o Raise KeyError if 'role_id' is unknown.
        """
        role_info = self._roles[ role_id ] # raise KeyError if unknown!

        current = self._principal_roles.get( principal_id, () )
        already = role_id in current

        if not already:
            new = current + ( role_id, )
            self._principal_roles[ principal_id ] = new

        return not already

    security.declareProtected( ManageUsers, 'removeRoleFromPrincipal' )
    def removeRoleFromPrincipal( self, role_id, principal_id ):

        """ Remove a role from a principal (user or group).

        o Return a boolean indicating whether the role was already present.

        o Raise KeyError if 'role_id' is unknown.

        o Ignore requests to remove a role not already assigned to the
          principal.
        """
        role_info = self._roles[ role_id ] # raise KeyError if unknown!

        current = self._principal_roles.get( principal_id, () )
        new = tuple( [ x for x in current if x != role_id ] )
        already = current != new

        if already:
            self._principal_roles[ principal_id ] = new

        return already

    #
    #   ZMI
    #
    manage_options = ( ( { 'label': 'Roles', 
                           'action': 'manage_roles', }
                         ,
                       )
                     + BasePlugin.manage_options
                     )

    security.declareProtected( ManageUsers, 'manage_roles' )
    manage_roles = PageTemplateFile( 'www/zrRoles'
                                   , globals()
                                   , __name__='manage_roles'
                                   )

    security.declareProtected( ManageUsers, 'manage_twoLists' )
    manage_twoLists = PageTemplateFile( '../www/two_lists'
                                      , globals()
                                      , __name__='manage_twoLists'
                                      )

    security.declareProtected( ManageUsers, 'manage_addRole' )
    def manage_addRole( self
                      , role_id
                      , title
                      , description
                      , RESPONSE
                      ):
        """ Add a role via the ZMI.
        """
        self.addRole( role_id, title, description )

        message = 'Role+added'

        RESPONSE.redirect( '%s/manage_roles?manage_tabs_message=%s'
                         % ( self.absolute_url(), message )
                         )

    security.declareProtected( ManageUsers, 'manage_updateRole' )
    def manage_updateRole( self
                         , role_id
                         , title
                         , description
                         , RESPONSE
                         ):
        """ Update a role via the ZMI.
        """
        self.updateRole( role_id, title, description )

        message = 'Role+updated'

        RESPONSE.redirect( '%s/manage_roles?role_id=%s&manage_tabs_message=%s'
                         % ( self.absolute_url(), role_id, message )
                         )

    security.declareProtected( ManageUsers, 'manage_removeRoles' )
    def manage_removeRoles( self
                          , role_ids
                          , RESPONSE
                          ):
        """ Remove one or more roles via the ZMI.
        """
        role_ids = filter( None, role_ids )

        if not role_ids:
            message = 'no+roles+selected'

        else:

            for role_id in role_ids:
                self.removeRole( role_id )

            message = 'Roles+removed'

        RESPONSE.redirect( '%s/manage_roles?manage_tabs_message=%s'
                         % ( self.absolute_url(), message )
                         )

    security.declareProtected( ManageUsers, 'manage_assignRoleToPrincipals' )
    def manage_assignRoleToPrincipals( self
                                     , role_id
                                     , principal_ids
                                     , RESPONSE
                                     ):
        """ Assign a role to one or more principals via the ZMI.
        """
        assigned = []

        for principal_id in principal_ids:
            if self.assignRoleToPrincipal( role_id, principal_id ):
                assigned.append( principal_id )

        if not assigned:
            message = 'Role+%s+already+assigned+to+all+principals' % role_id
        else:
            message = 'Role+%s+assigned+to+%s' % ( role_id
                                                 , '+'.join( assigned )
                                                 )

        RESPONSE.redirect( ( '%s/manage_roles?role_id=%s&assign=1'
                           + '&manage_tabs_message=%s'
                           ) % ( self.absolute_url(), role_id, message )
                         )

    security.declareProtected( ManageUsers, 'manage_removeRoleFromPrincipals' )
    def manage_removeRoleFromPrincipals( self
                                       , role_id
                                       , principal_ids
                                       , RESPONSE
                                       ):
        """ Remove a role from one or more principals via the ZMI.
        """
        removed = []

        for principal_id in principal_ids:
            if self.removeRoleFromPrincipal( role_id, principal_id ):
                removed.append( principal_id )

        if not removed:
            message = 'Role+%s+alread+removed+from+all+principals' % role_id
        else:
            message = 'Role+%s+removed+from+%s' % ( role_id
                                                  , '+'.join( removed )
                                                  )

        RESPONSE.redirect( ( '%s/manage_roles?role_id=%s&assign=1'
                           + '&manage_tabs_message=%s'
                           ) % ( self.absolute_url(), role_id, message )
                         )

classImplements( ZODBRoleManager
               , IZODBRoleManager
               , IRolesPlugin
               , IRoleEnumerationPlugin
               , IRoleAssignerPlugin
               )


InitializeClass( ZODBRoleManager )

class _ZODBRoleFilter:

    def __init__( self, id=None, **kw ):

        self._filter_ids = id

    def __call__( self, role_info ):

        if self._filter_ids:

            key = 'id'

        else:
            return 1 # TODO:  try using 'kw'

        value = role_info.get( key )

        if not value:
            return False

        for id in self._filter_ids:
            if value.find( id ) >= 0:
                return 1

        return False
