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
""" Classes: DynamicGroupsPlugin

$Id: DynamicGroupsPlugin.py 40169 2005-11-16 20:09:11Z tseaver $
"""
import copy

from Acquisition import aq_inner, aq_parent
from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from OFS.Folder import Folder
from OFS.Cache import Cacheable
from Globals import InitializeClass
from Persistence import PersistentMapping

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PageTemplates.Expressions import getEngine

from Products.PluggableAuthService.interfaces.plugins \
    import IGroupsPlugin
from Products.PluggableAuthService.interfaces.plugins \
    import IGroupEnumerationPlugin
from Products.PluggableAuthService.permissions import ManageGroups
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import createViewName
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class IDynamicGroupsPlugin(Interface):
    """ Marker interface.
    """


manage_addDynamicGroupsPluginForm = PageTemplateFile(
        'www/dgpAdd', globals(), __name__= 'manage_addDynamicGroupsPluginForm' )

def addDynamicGroupsPlugin( dispatcher, id, title='', RESPONSE=None ):

    """ Add a DGP to 'dispatcher'.
    """
    dgp = DynamicGroupsPlugin( id, title )
    dispatcher._setObject( id, dgp )

    if RESPONSE is not None:
        RESPONSE.redirect( '%s/manage_main?manage_tabs_messsage=%s'
                         % ( dispatcher.absolute_url()
                           , 'DPG+added.'
                           )
                         )

class DynamicGroupDefinition( SimpleItem, PropertyManager ):

    """ Represent a single dynamic group.
    """
    meta_type = 'Dynamic Group Definition'
    security = ClassSecurityInfo()
    security.declareObjectProtected( ManageGroups )

    _v_compiled = None


    _properties = ( { 'id' : 'id'
                    , 'type' : 'string'
                    , 'mode' : ''
                    }
                  , { 'id' : 'predicate'
                    , 'type' : 'string'
                    , 'mode' : 'w'
                    }
                  , { 'id' : 'title'
                    , 'type' : 'string'
                    , 'mode' : 'w'
                    }
                  , { 'id' : 'description'
                    , 'type' : 'text'
                    , 'mode' : 'w'
                    }
                  , { 'id' : 'active'
                    , 'type' : 'boolean'
                    , 'mode' : 'w'
                    }
                  )

    def __init__( self, id, predicate, title, description, active ):

        self._setId( id )
        self._setPredicate( predicate )

        self.title = title
        self.description = description
        self.active = bool( active )

    def __call__( self, principal, request=None ):

        """ Evaluate our expression to determine whether 'principal' belongs.
        """
        predicate = self._getPredicate()
        plugin = aq_parent( aq_inner( self ) )
        properties = {}

        for k, v in self.propertyItems():
            properties[ k ] = v

        data = getEngine().getContext( { 'request' :    request
                                       , 'nothing' :    None
                                       , 'principal' :  principal
                                       , 'group' :      properties
                                       , 'plugin' :     plugin
                                       } )

        result = predicate( data )

        if isinstance( result, Exception ):
            raise result

        return result

    security.declarePrivate( '_setPredicate' )
    def _setPredicate( self, predicate ):

        self.predicate = predicate

        if self._v_compiled is not None:
            del self._v_compiled

    security.declarePrivate( '_getPredicate' )
    def _getPredicate( self ):

        if self._v_compiled is None:
            self._v_compiled = getEngine().compile( self.predicate )

        return self._v_compiled

    security.declarePrivate( '_updateProperty' )
    def _updateProperty( self, id, value ):

        if id == 'predicate':
            self._setPredicate( value )

        else:
            PropertyManager._updateProperty( self, id, value )

    #
    #   ZMI
    #
    manage_options = ( PropertyManager.manage_options
                     + SimpleItem.manage_options
                     )

InitializeClass( DynamicGroupDefinition )


class DynamicGroupsPlugin( Folder, BasePlugin, Cacheable ):

    """ Define groups via business rules.

    o Membership in a candidate group is established via a predicate,
      expressed as a TALES expression.  Names available to the predicate
      include:

      'group' -- the dynamic group definition object itself

      'plugin' -- this plugin object

      'principal' -- the principal being tested.

      'request' -- the request object.
    """
    meta_type = 'Dynamic Groups Plugin'

    security = ClassSecurityInfo()

    def __init__( self, id, title='' ):

        self._setId( id )
        self.title = title

    #
    #   Plugin implementations
    #
    security.declareProtected( ManageGroups, 'getGroupsForPrincipal' )
    def getGroupsForPrincipal( self, principal, request=None ):

        """ See IGroupsPlugin.
        """
        grps = []
        DGD = DynamicGroupDefinition.meta_type
        for group in self.objectValues( DGD ):
            if group.active and group( principal, request ):
                grps.append('%s%s' % (self.prefix, group.getId()))
        return grps

    security.declareProtected( ManageGroups, 'enumerateGroups' )
    def enumerateGroups( self
                       , id=None
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
        view_name = createViewName('enumerateGroups', id)

        # Look in the cache first...
        keywords = copy.deepcopy(kw)
        keywords.update( { 'id' : id
                         , 'exact_match' : exact_match
                         , 'sort_by' : sort_by
                         , 'max_results' : max_results
                         }
                       )
        cached_info = self.ZCacheable_get( view_name=view_name
                                         , keywords=keywords
                                         , default=None
                                         )

        if cached_info is not None:
            return tuple(cached_info)

        if isinstance( id, str ):
            id = [ id ]

        if exact_match and id:
            group_ids.extend( id )

        if group_ids:
            group_filter = None

        else:   # Searching
            group_ids = self.listGroupIds()
            group_filter = _DynamicGroupFilter( id, **kw )

        for group_id in group_ids:

            url = '/%s/%s/manage_propertiesForm' % ( self.absolute_url( 1 )
                                                   , group_id )
            info = {}
            info.update( self.getGroupInfo( group_id ) )

            info[ 'pluginid' ] = plugin_id
            info[ 'properties_url' ] = url
            info[ 'members_url' ] = url

            info[ 'id' ] = '%s%s' % (self.prefix, info['id'])

            if not group_filter or group_filter( info ):
                if info[ 'active' ]:
                    group_info.append( info )

        # Put the computed value into the cache
        self.ZCacheable_set(group_info, view_name=view_name, keywords=keywords)

        return tuple( group_info )

    #
    #   Housekeeping
    #
    security.declareProtected( ManageGroups, 'listGroupIds' )
    def listGroupIds( self ):

        """ Return a list of IDs for the dynamic groups we manage.
        """
        return self.objectIds( DynamicGroupDefinition.meta_type )

    security.declareProtected( ManageGroups, 'getGroupInfo' )
    def getGroupInfo( self, group_id ):

        """ Return a mappings describing one dynamic group we manage.

        o Raise KeyError if we don't have an existing group definition
          for 'group_ id'.

        o Keys include:

          'id' -- the group's ID

          'predicate' -- the TALES expression defining group membership

          'active' -- boolean flag:  is the group currently active?
        """
        try:
            original = self._getOb( group_id )
        except AttributeError:
            try:
                original = self._getOb( group_id[len(self.prefix):] )
            except AttributeError:
                raise KeyError, group_id

        if not isinstance( original, DynamicGroupDefinition ):
            raise KeyError, group_id

        info = {}

        for k, v in original.propertyItems():
            info[ k ] = v

        return info

    security.declareProtected( ManageGroups, 'listGroupInfo' )
    def listGroupInfo( self ):

        """ Return a list of mappings describing the dynamic groups we manage.

        o Keys include:

          'id' -- the group's ID

          'predicate' -- the TALES expression defining group membership

          'active' -- boolean flag:  is the group currently active?
        """
        return [ self.getGroupInfo( x ) for x in self.listGroupIds() ]

    security.declareProtected( ManageGroups, 'addGroup' )
    def addGroup( self
                , group_id
                , predicate
                , title=''
                , description=''
                , active=True
                ):

        """ Add a group definition.

        o Raise KeyError if we have an existing group definition
          for 'group_id'.
        """
        if group_id in self.listGroupIds():
            raise KeyError, 'Duplicate group ID: %s' % group_id

        info = DynamicGroupDefinition( group_id
                                     , predicate
                                     , title
                                     , description
                                     , active
                                     )

        self._setObject( group_id, info )

        # This method changes the enumerateGroups return value
        view_name = createViewName('enumerateGroups')
        self.ZCacheable_invalidate(view_name=view_name)
            
    security.declareProtected( ManageGroups, 'updateGroup' )
    def updateGroup( self
                   , group_id
                   , predicate
                   , title=None
                   , description=None
                   , active=None
                   ):

        """ Update a group definition.

        o Raise KeyError if we don't have an existing group definition
          for 'group_id'.

        o Don't update 'title', 'description', or 'active' unless supplied.
        """
        if group_id not in self.listGroupIds():
            raise KeyError, 'Invalid group ID: %s' % group_id

        group = self._getOb( group_id )

        group._setPredicate( predicate )

        if title is not None:
            group.title = title

        if description is not None:
            group.description = description

        if active is not None:
            group.active = active

        # This method changes the enumerateGroups return value
        view_name = createViewName('enumerateGroups')
        self.ZCacheable_invalidate(view_name=view_name)
        view_name = createViewName('enumerateGroups', group_id)
        self.ZCacheable_invalidate(view_name=view_name)
            
    security.declareProtected( ManageGroups, 'removeGroup' )
    def removeGroup( self, group_id ):

        """ Remove a group definition.

        o Raise KeyError if we don't have an existing group definition
          for 'group_id'.
        """
        if group_id not in self.listGroupIds():
            raise KeyError, 'Invalid group ID: %s' % group_id

        self._delObject( group_id )

        # This method changes the enumerateGroups return value
        view_name = createViewName('enumerateGroups')
        self.ZCacheable_invalidate(view_name=view_name)
        view_name = createViewName('enumerateGroups', group_id)
        self.ZCacheable_invalidate(view_name=view_name)

    #
    #   ZMI
    #
    manage_options = ( ( { 'label' : 'Groups'
                         , 'action' : 'manage_groups'
                         }
                       ,
                       )
                     + Folder.manage_options[:1]
                     + BasePlugin.manage_options[:1]
                     + Folder.manage_options[1:]
                     + Cacheable.manage_options
                     )

    manage_groups = PageTemplateFile( 'www/dgpGroups'
                                    , globals()
                                    , __name__='manage_groups'
                                    )

    security.declareProtected( ManageGroups, 'manage_addGroup' )
    def manage_addGroup( self
                       , group_id
                       , title
                       , description
                       , predicate
                       , active=True
                       , RESPONSE=None
                       ):
        """ Add a group via the ZMI.
        """
        self.addGroup( group_id
                     , predicate
                     , title
                     , description
                     , active
                     )

        message = 'Group+%s+added' % group_id

        if RESPONSE is not None:
            RESPONSE.redirect( '%s/manage_groups?manage_tabs_message=%s'
                            % ( self.absolute_url(), message )
                            )

    security.declareProtected( ManageGroups, 'manage_updateGroup' )
    def manage_updateGroup( self
                          , group_id
                          , predicate
                          , title=None
                          , description=None
                          , active=True
                          , RESPONSE=None
                          ):
        """ Update a group via the ZMI.
        """
        self.updateGroup( group_id
                        , predicate
                        , title
                        , description
                        , active
                        )

        message = 'Group+%s+updated' % group_id

        if RESPONSE is not None:
            RESPONSE.redirect( ( '%s/manage_groups?group_id=%s&'
                               + 'manage_tabs_message=%s'
                               ) % ( self.absolute_url(), group_id, message )
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

classImplements( DynamicGroupsPlugin
               , IDynamicGroupsPlugin
               , IGroupsPlugin
               , IGroupEnumerationPlugin
               )

InitializeClass( DynamicGroupsPlugin )

class _DynamicGroupFilter:

    def __init__( self
                , id=None
                , **kw
                ):

        self._filter_ids = id

    def __call__( self, group_info ):

        if self._filter_ids:

            key = 'id'

        else:
            return 1 # TODO:  try using 'kw'

        value = group_info.get( key )

        if not value:
            return 0

        for id in self._filter_ids:
            if value.find( id ) >= 0:
                return 1

        return 0
