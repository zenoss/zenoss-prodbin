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
""" Classes: ZODBGroupManager

$Id: ZODBGroupManager.py 65456 2006-02-25 18:51:23Z jens $
"""
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from BTrees.OOBTree import OOBTree
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins \
    import IGroupEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins \
    import IGroupsPlugin

from Products.PluggableAuthService.permissions import ManageGroups
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class IZODBGroupManager(Interface):
    """ Marker interface.
    """

manage_addZODBGroupManagerForm = PageTemplateFile(
    'www/zgAdd', globals(), __name__='manage_addZODBGroupManagerForm' )

def addZODBGroupManager( dispatcher, id, title=None, REQUEST=None ):
    """ Add a ZODBGroupManager to a Pluggable Auth Service. """

    zgm = ZODBGroupManager(id, title)
    dispatcher._setObject(zgm.getId(), zgm)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(
                                '%s/manage_workspace'
                                '?manage_tabs_message='
                                'ZODBGroupManager+added.'
                            % dispatcher.absolute_url())

class ZODBGroupManager( BasePlugin ):

    """ PAS plugin for managing groups, and groups of groups in the ZODB
    """
    meta_type = 'ZODB Group Manager'

    security = ClassSecurityInfo()

    def __init__(self, id, title=None):

        self._id = self.id = id
        self.title = title
        self._groups = OOBTree()
        self._principal_groups = OOBTree()

    #
    #   IGroupEnumerationPlugin implementation
    #
    security.declarePrivate( 'enumerateGroups' )
    def enumerateGroups( self
                        , id=None
                        , title=None
                        , exact_match=False
                        , sort_by=None
                        , max_results=None
                        , **kw
                        ):

        """ See IGroupEnumerationPlugin.
        """
        group_info = []
        group_ids = []
        plugin_id = self.getId()

        if isinstance( id, str ):
            id = [ id ]

        if isinstance( title, str ):
            title = [ title ]

        if exact_match and ( id or title ):

            if id:
                group_ids.extend( id )
            elif title:
                group_ids.extend( title )

        if group_ids:
            group_filter = None

        else:   # Searching
            group_ids = self.listGroupIds()
            group_filter = _ZODBGroupFilter( id, title, **kw )

        for group_id in group_ids:

            if self._groups.get( group_id, None ):
                e_url = '%s/manage_groups' % self.getId()
                p_qs = 'group_id=%s' % group_id
                m_qs = 'group_id=%s&assign=1' % group_id

                info = {}
                info.update( self._groups[ group_id ] )

                info[ 'pluginid' ] = plugin_id
                info[ 'properties_url' ] = '%s?%s' % ( e_url, p_qs )
                info[ 'members_url' ] = '%s?%s' % ( e_url, m_qs )

                info[ 'id' ] = '%s%s' % (self.prefix, info['id'])

                if not group_filter or group_filter( info ):
                    group_info.append( info )

        return tuple( group_info )

    #
    #   IGroupsPlugin implementation
    #
    security.declarePrivate( 'getGroupsForPrincipal' )
    def getGroupsForPrincipal( self, principal, request=None ):

        """ See IGroupsPlugin.
        """
        unadorned = self._principal_groups.get( principal.getId(), () )
        return tuple(['%s%s' % (self.prefix, x) for x in unadorned])

    #
    #   (notional)IZODBGroupManager interface
    #
    security.declareProtected( ManageGroups, 'listGroupIds' )
    def listGroupIds( self ):

        """ -> ( group_id_1, ... group_id_n )
        """
        return self._groups.keys()

    security.declareProtected( ManageGroups, 'listGroupInfo' )
    def listGroupInfo( self ):

        """ -> ( {}, ...{} )

        o Return one mapping per group, with the following keys:

          - 'id' 
        """
        return self._groups.values()

    security.declareProtected( ManageGroups, 'getGroupInfo' )
    def getGroupInfo( self, group_id ):

        """ group_id -> {}
        """
        return self._groups[ group_id ]

    security.declarePrivate( 'addGroup' )
    def addGroup( self, group_id, title=None, description=None ):

        """ Add 'group_id' to the list of groups managed by this object.

        o Raise KeyError on duplicate.
        """
        if self._groups.get( group_id ) is not None:
            raise KeyError, 'Duplicate group ID: %s' % group_id

        self._groups[ group_id ] = { 'id' : group_id
                                   , 'title' : title
                                   , 'description' : description
                                   }

    security.declarePrivate( 'updateGroup' )
    def updateGroup( self, group_id, title, description ):

        """ Update properties for 'group_id'

        o Raise KeyError if group_id doesn't already exist.
        """
        self._groups[ group_id ].update({ 'title' : title
                                        , 'description' : description
                                        })
        self._groups[ group_id ] = self._groups[ group_id ]

    security.declarePrivate( 'removeGroup' )
    def removeGroup( self, group_id ):

        """ Remove 'role_id' from the list of roles managed by this
            object, removing assigned members from it before doing so.

        o Raise KeyError if 'group_id' doesn't already exist.
        """
        for principal_id in self._principal_groups.keys():
            self.removePrincipalFromGroup( principal_id, group_id )
        del self._groups[ group_id ]

    #
    #   Group assignment API
    #
    security.declareProtected( ManageGroups, 'listAvailablePrincipals' )
    def listAvailablePrincipals( self, group_id, search_id ):

        """ Return a list of principal IDs to that can belong to the group.

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
                if ( group_id not in self._principal_groups.get( id, () )
                 and group_id != id ):
                    result.append( ( id, title ) )

        return result

    security.declareProtected( ManageGroups, 'listAssignedPrincipals' )
    def listAssignedPrincipals( self, group_id ):

        """ Return a list of principal IDs belonging to a group.
        """
        result = []

        for k, v in self._principal_groups.items():
            if group_id in v:
                # should be one and only one mapping to 'k'

                parent = aq_parent( self )
                info = parent.searchPrincipals( id=k, exact_match=True )
                assert( len( info ) in ( 0, 1 ) )
                if len( info ) == 0:
                    title = '<%s: not found>' % k
                else:
                    title = info[0].get( 'title', k )
                result.append( ( k, title ) )

        return result

    security.declareProtected( ManageGroups, 'addPrincipalToGroup' )
    def addPrincipalToGroup( self, principal_id, group_id ):

        """ Add a principal to a group.

        o Return a boolean indicating whether a new assignment was created.

        o Raise KeyError if 'group_id' is unknown.
        """
        group_info = self._groups[ group_id ] # raise KeyError if unknown!

        current = self._principal_groups.get( principal_id, () )
        already = group_id in current

        if not already:
            new = current + ( group_id, )
            self._principal_groups[ principal_id ] = new

        return not already

    security.declareProtected( ManageGroups, 'removePrincipalFromGroup' )
    def removePrincipalFromGroup( self, principal_id, group_id ):

        """ Remove a prinicpal from from a group.

        o Return a boolean indicating whether the principal was already 
          a member of the group.

        o Raise KeyError if 'group_id' is unknown.

        o Ignore requests to remove a principal if not already a member
          of the group.
        """
        group_info = self._groups[ group_id ] # raise KeyError if unknown!

        current = self._principal_groups.get( principal_id, () )
        new = tuple( [ x for x in current if x != group_id ] )
        already = current != new

        if already:
            self._principal_groups[ principal_id ] = new

        return already

    #
    #   ZMI
    #
    manage_options = ( ( { 'label': 'Groups', 
                           'action': 'manage_groups', }
                         ,
                       )
                     + BasePlugin.manage_options
                     )

    security.declarePublic( 'manage_widgets' )
    manage_widgets = PageTemplateFile( 'www/zuWidgets'
                                     , globals()
                                     , __name__='manage_widgets'
                                     )

    security.declareProtected( ManageGroups, 'manage_groups' )
    manage_groups = PageTemplateFile( 'www/zgGroups'
                                    , globals()
                                    , __name__='manage_groups'
                                    )

    security.declareProtected( ManageGroups, 'manage_twoLists' )
    manage_twoLists = PageTemplateFile( '../www/two_lists'
                                      , globals()
                                      , __name__='manage_twoLists'
                                      )

    security.declareProtected( ManageGroups, 'manage_addGroup' )
    def manage_addGroup( self
                       , group_id
                       , title=None
                       , description=None
                       , RESPONSE=None
                       ):
        """ Add a group via the ZMI.
        """
        self.addGroup( group_id, title, description )

        message = 'Group+added'

        if RESPONSE is not None:
            RESPONSE.redirect( '%s/manage_groups?manage_tabs_message=%s'
                             % ( self.absolute_url(), message )
                             )

    security.declareProtected( ManageGroups, 'manage_updateGroup' )
    def manage_updateGroup( self
                          , group_id
                          , title
                          , description
                          , RESPONSE=None
                          ):
        """ Update a group via the ZMI.
        """
        self.updateGroup( group_id, title, description )

        message = 'Group+updated'

        if RESPONSE is not None:
            RESPONSE.redirect( '%s/manage_groups?manage_tabs_message=%s'
                             % ( self.absolute_url(), message )
                             )

    security.declareProtected( ManageGroups, 'manage_removeGroups' )
    def manage_removeGroups( self
                           , group_ids
                           , RESPONSE=None
                           ):
        """ Remove one or more groups via the ZMI.
        """
        group_ids = filter( None, group_ids )

        if not group_ids:
            message = 'no+groups+selected'

        else:

            for group_id in group_ids:
                self.removeGroup( group_id )

            message = 'Groups+removed'

        if RESPONSE is not None:
            RESPONSE.redirect( '%s/manage_groups?manage_tabs_message=%s'
                             % ( self.absolute_url(), message )
                             )

    security.declareProtected( ManageGroups, 'manage_addPrincipalsToGroup' )
    def manage_addPrincipalsToGroup( self
                                   , group_id
                                   , principal_ids
                                   , RESPONSE=None
                                   ):
        """ Add one or more principals to a group via the ZMI.
        """
        assigned = []

        for principal_id in principal_ids:
            if self.addPrincipalToGroup( principal_id, group_id ):
                assigned.append( principal_id )

        if not assigned:
            message = 'Principals+already+members+of+%s' % group_id
        else:
            message = '%s+added+to+%s' % ( '+'.join( assigned )
                                         , group_id
                                         )

        if RESPONSE is not None:
            RESPONSE.redirect( ( '%s/manage_groups?group_id=%s&assign=1'
                               + '&manage_tabs_message=%s'
                               ) % ( self.absolute_url(), group_id, message )
                             )

    security.declareProtected( ManageGroups
                             , 'manage_removePrincipalsFromGroup' 
                             )
    def manage_removePrincipalsFromGroup( self
                                        , group_id
                                        , principal_ids
                                        , RESPONSE=None
                                        ):
        """ Remove one or more principals from a group via the ZMI.
        """
        removed = []

        for principal_id in principal_ids:
            if self.removePrincipalFromGroup( principal_id, group_id ):
                removed.append( principal_id )

        if not removed:
            message = 'Principals+not+in+group+%s' % group_id
        else:
            message = 'Principals+%s+removed+from+%s' % ( '+'.join( removed )
                                                        , group_id
                                                        )

        if RESPONSE is not None:
            RESPONSE.redirect( ( '%s/manage_groups?group_id=%s&assign=1'
                               + '&manage_tabs_message=%s'
                               ) % ( self.absolute_url(), group_id, message )
                             )

classImplements( ZODBGroupManager
               , IZODBGroupManager
               , IGroupEnumerationPlugin
               , IGroupsPlugin
               )

InitializeClass( ZODBGroupManager )

class _ZODBGroupFilter:

    def __init__( self
                , id=None
                , title=None
                , **kw
                ):

        self._filter_ids = id
        self._filter_titles = title

    def __call__( self, group_info ):

        if self._filter_ids:

            key = 'id'
            to_test = self._filter_ids

        elif self._filter_titles:

            key = 'title'
            to_test = self._filter_titles

        else:
            return 1 # TODO:  try using 'kw'

        value = group_info.get( key )

        if not value:
            return 0

        for contained in to_test:
            if value.lower().find( contained.lower() ) >= 0:
                return 1

        return 0
