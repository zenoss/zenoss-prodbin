##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
""" Classes: PluginRegistry

$Id: PluginRegistry.py 69261 2006-07-25 22:09:23Z tseaver $
"""

from Globals import Persistent
from App.ImageFile import ImageFile
from Acquisition import Implicit, aq_parent, aq_inner
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import manage_users as ManageUsers
from Persistence import PersistentMapping
from OFS.SimpleItem import SimpleItem
from App.class_init import default__class_init__ as InitializeClass

try:
    from webdav.interfaces import IWriteLock
except ImportError:
    try:
        from Products.Five.interfaces import IWriteLock
    except ImportError:
        _HAS_Z3_DAV_INTERFACES = False
        from webdav.WriteLockInterface import WriteLockInterface
    else:
        _HAS_Z3_DAV_INTERFACES = True
else:
    _HAS_Z3_DAV_INTERFACES = True

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PageTemplates.Expressions import getEngine
from Products.PageTemplates.Expressions import SecureModuleImporter

from interfaces import IPluginRegistry
from interfaces import _HAS_Z3_INTERFACES
if _HAS_Z3_INTERFACES:
    from zope.interface import implements

try:
    from exportimport import _updatePluginRegistry
except ImportError:
    _HAS_GENERIC_SETUP = False
else:
    _HAS_GENERIC_SETUP = True

from utils import _wwwdir

class PluginRegistry( SimpleItem ):

    """ Implement IPluginRegistry as an independent, ZMI-manageable object.

    o Each plugin type holds an ordered list of ( id, wrapper ) tuples.
    """
    if _HAS_Z3_INTERFACES:
        if _HAS_Z3_DAV_INTERFACES:
            implements(IPluginRegistry, IWriteLock)
        else:
            implements(IPluginRegistry)
            __implements__ = (WriteLockInterface,)
    else:
        __implements__ = (IPluginRegistry, WriteLockInterface,)

    security = ClassSecurityInfo()

    meta_type = 'Plugin Registry'

    _plugins = None

    def __init__( self, plugin_type_info=() ):

        if isinstance(plugin_type_info, basestring):
            # some tool is passing us our ID.
            raise ValueError('Must pass a sequence of plugin info dicts!')

        self._plugin_types = [x[0] for x in plugin_type_info]
        self._plugin_type_info = PersistentMapping()
        for interface in plugin_type_info:
            self._plugin_type_info[interface[0]] = { 
                  'id': interface[1]
                , 'title': interface[2]
                , 'description': interface[3]
                }

    #
    #   IPluginRegistry implementation
    #
    security.declareProtected( ManageUsers, 'listPluginTypeInfo' )
    def listPluginTypeInfo( self ):

        """ See IPluginRegistry.
        """
        result = []

        for ptype in self._plugin_types:

            info = self._plugin_type_info[ptype].copy()
            info['interface'] = ptype
            info['methods'] = ptype.names()

            result.append( info )

        return result

    security.declareProtected( ManageUsers, 'listPlugins' )
    def listPlugins( self, plugin_type ):

        """ See IPluginRegistry.
        """
        result = []

        parent = aq_parent( aq_inner( self ) )

        for plugin_id in self._getPlugins( plugin_type ):

            plugin = parent._getOb( plugin_id )
            result.append( ( plugin_id, plugin ) )

        return result

    security.declareProtected( ManageUsers, 'getPluginInfo' )
    def getPluginInfo( self, plugin_type ):

        """ See IPluginRegistry.
        """
        plugin_type = self._getInterfaceFromName( plugin_type )
        return self._plugin_type_info[plugin_type]

    security.declareProtected( ManageUsers, 'listPluginIds' )
    def listPluginIds( self, plugin_type ):

        """ See IPluginRegistry.
        """

        return self._getPlugins( plugin_type )

    security.declareProtected( ManageUsers, 'activatePlugin' )
    def activatePlugin( self, plugin_type, plugin_id ):

        """ See IPluginRegistry.
        """
        plugins = list( self._getPlugins( plugin_type ) )

        if plugin_id in plugins:
            raise KeyError, 'Duplicate plugin id: %s' % plugin_id

        parent = aq_parent( aq_inner( self ) )
        plugin = parent._getOb( plugin_id ) 

        satisfies = getattr(plugin_type, 'providedBy', None)
        if satisfies is None:
            satisfies = plugin_type.isImplementedBy

        if not satisfies(plugin):
            raise ValueError, 'Plugin does not implement %s' % plugin_type 
        
        plugins.append( plugin_id )
        self._plugins[ plugin_type ] = tuple( plugins )

    security.declareProtected( ManageUsers, 'deactivatePlugin' )
    def deactivatePlugin( self, plugin_type, plugin_id ):

        """ See IPluginRegistry.
        """
        plugins = list( self._getPlugins( plugin_type ) )

        if not plugin_id in plugins:
            raise KeyError, 'Invalid plugin id: %s' % plugin_id

        plugins = [ x for x in plugins if x != plugin_id ]
        self._plugins[ plugin_type ] = tuple( plugins )

    security.declareProtected( ManageUsers, 'movePluginsUp' )
    def movePluginsUp( self, plugin_type, ids_to_move ):

        """ See IPluginRegistry.
        """
        ids = list( self._getPlugins( plugin_type ) )
        count = len( ids )

        indexes = list( map( ids.index, ids_to_move ) )
        indexes.sort()

        for i1 in indexes:

            if i1 < 0 or i1 >= count:
                raise IndexError, i1

            i2 = i1 - 1
            if i2 < 0:      # wrap to bottom
                i2 = len( ids ) - 1

            ids[ i2 ], ids[ i1 ] = ids[ i1 ], ids[ i2 ]

        self._plugins[ plugin_type ] = tuple( ids )

    security.declareProtected( ManageUsers, 'movePluginsDown' )
    def movePluginsDown( self, plugin_type, ids_to_move ):

        """ See IPluginRegistry.
        """
        ids = list( self._getPlugins( plugin_type ) )
        count = len( ids )

        indexes = list( map( ids.index, ids_to_move ) )
        indexes.sort()
        indexes.reverse()

        for i1 in indexes:

            if i1 < 0 or i1 >= count:
                raise IndexError, i1

            i2 = i1 + 1
            if i2 == len( ids ):      # wrap to top
                i2 = 0

            ids[ i2 ], ids[ i1 ] = ids[ i1 ], ids[ i2 ]

        self._plugins[ plugin_type ] = tuple( ids )

    #
    #   ZMI
    #
    arrow_right_gif = ImageFile( 'www/arrow-right.gif', globals() )
    arrow_left_gif = ImageFile( 'www/arrow-left.gif', globals() )
    arrow_up_gif = ImageFile( 'www/arrow-up.gif', globals() )
    arrow_down_gif = ImageFile( 'www/arrow-down.gif', globals() )

    security.declareProtected( ManageUsers, 'manage_activatePlugins' )
    def manage_activatePlugins( self
                             , plugin_type
                             , plugin_ids
                             , RESPONSE
                             ):
        """ Shim into ZMI.
        """
        interface = self._getInterfaceFromName( plugin_type )
        for id in plugin_ids:
            self.activatePlugin( interface, id )
        RESPONSE.redirect( '%s/manage_plugins?plugin_type=%s'
                         % ( self.absolute_url(), plugin_type )
                         )

    security.declareProtected( ManageUsers, 'manage_deactivatePlugins' )
    def manage_deactivatePlugins( self
                                , plugin_type
                                , plugin_ids
                                , RESPONSE
                                ):
        """ Shim into ZMI.
        """
        interface = self._getInterfaceFromName( plugin_type )
        for id in plugin_ids:
            self.deactivatePlugin( interface, id )

        RESPONSE.redirect( '%s/manage_plugins?plugin_type=%s'
                         % ( self.absolute_url(), plugin_type )
                         )

    security.declareProtected( ManageUsers, 'manage_movePluginsUp' )
    def manage_movePluginsUp( self
                            , plugin_type
                            , plugin_ids
                            , RESPONSE
                            ):
        """ Shim into ZMI.
        """
        interface = self._getInterfaceFromName( plugin_type )
        self.movePluginsUp( interface, plugin_ids )

        RESPONSE.redirect( '%s/manage_plugins?plugin_type=%s'
                         % ( self.absolute_url(), plugin_type )
                         )

    security.declareProtected( ManageUsers, 'manage_movePluginsDown' )
    def manage_movePluginsDown( self
                              , plugin_type
                              , plugin_ids
                              , RESPONSE
                              ):
        """ Shim into ZMI.
        """
        interface = self._getInterfaceFromName( plugin_type )
        self.movePluginsDown( interface, plugin_ids )

        RESPONSE.redirect( '%s/manage_plugins?plugin_type=%s'
                         % ( self.absolute_url(), plugin_type )
                         )

    security.declareProtected( ManageUsers, 'getAllPlugins' )
    def getAllPlugins( self, plugin_type ):

        """ Return a mapping segregating active / available plugins.

        'plugin_type' is the __name__ of the interface.
        """
        interface = self._getInterfaceFromName( plugin_type )

        active = self._getPlugins( interface )
        available = []

        satisfies = getattr(interface, 'providedBy', None)
        if satisfies is None:
            satisfies = interface.isImplementedBy

        for id, value in aq_parent( aq_inner( self ) ).objectItems():
            if satisfies( value ):
                if id not in active:
                    available.append( id )

        return { 'active' : active, 'available' : available }


    security.declareProtected( ManageUsers, 'removePluginById' )
    def removePluginById( self, plugin_id ):

        """ Remove a plugin from any plugin types which have it configured.
        """
        for plugin_type in self._plugin_types:

            if plugin_id in self._getPlugins( plugin_type ):
                self.deactivatePlugin( plugin_type, plugin_id )

    security.declareProtected( ManageUsers, 'manage_plugins' )
    manage_plugins = PageTemplateFile( 'plugins', _wwwdir )
    security.declareProtected( ManageUsers, 'manage_active' )
    manage_active = PageTemplateFile( 'active_plugins', _wwwdir )
    manage_twoLists = PageTemplateFile( 'two_lists', _wwwdir )

    manage_options=( ( { 'label'  : 'Plugins'
                       , 'action' : 'manage_plugins'
                     # , 'help'   : ( 'PluggableAuthService'
                     #              , 'plugins.stx')
                       }
                     , { 'label'  : 'Active'
                       , 'action' : 'manage_active'
                       }
                     )
                   + SimpleItem.manage_options
                   )

    if _HAS_GENERIC_SETUP:
        security.declareProtected( ManageUsers, 'manage_exportImportForm' )
        manage_exportImportForm = PageTemplateFile( 'export_import', _wwwdir )

        security.declareProtected( ManageUsers, 'getConfigAsXML' )
        def getConfigAsXML(self):
            """ Return XML representing the registry's configuration.
            """
            from exportimport import PluginRegistryExporter
            pre = PluginRegistryExporter(self).__of__(self)
            return pre.generateXML()

        security.declareProtected( ManageUsers, 'manage_exportImport' )
        def manage_exportImport(self, updated_xml, should_purge, RESPONSE):
            """ Parse XML and update the registry.
            """
            #XXX encoding?
            _updatePluginRegistry(self, updated_xml, should_purge)
            RESPONSE.redirect('%s/manage_exportImportForm'
                              '?manage_tabs_message=Registry+updated.'
                                % self.absolute_url())

        security.declareProtected( ManageUsers, 'manage_FTPget' )
        def manage_FTPget(self, REQUEST, RESPONSE):
            """
            """
            return self.getConfigAsXML()

        security.declareProtected( ManageUsers, 'PUT' )
        def PUT(self, REQUEST, RESPONSE):
            """
            """
            xml = REQUEST['BODYFILE'].read()
            _updatePluginRegistry(self, xml, True)

        manage_options = ( manage_options[:2]
                         + ( { 'label' : 'Export / Import'
                             , 'action' : 'manage_exportImportForm'
                             },)
                         + manage_options[2:]
                         )

    #
    #   Helper methods
    #
    security.declarePrivate( '_getPlugins' )
    def _getPlugins( self, plugin_type ):

        parent = aq_parent( aq_inner( self ) )

        if plugin_type not in self._plugin_types:
            raise KeyError, plugin_type

        if self._plugins is None:
            self._plugins = PersistentMapping()

        return self._plugins.setdefault( plugin_type, () )

    security.declarePrivate( '_getInterfaceFromName' )
    def _getInterfaceFromName( self, plugin_type_name ):

        """ Convert the string name to an interface.

        o Raise KeyError is no such interface is known.
        """
        found = [ x[0] for x in self._plugin_type_info.items()
                                if x[1][ 'id' ] == plugin_type_name ]
        if not found:
            raise KeyError, plugin_type_name

        if len( found ) > 1:
            raise KeyError, 'Waaa!:  %s' % plugin_type_name

        return found[ 0 ]

InitializeClass( PluginRegistry )

def emptyPluginRegistry( ignored ):
    """ Return empty registry, for filling from setup profile.
    """
    return PluginRegistry(())
