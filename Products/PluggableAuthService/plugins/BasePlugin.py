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
""" Class: BasePlugin

$Id: BasePlugin.py 39312 2005-07-06 18:49:05Z urbanape $
"""
from OFS.SimpleItem import SimpleItem
from OFS.PropertyManager import PropertyManager
from Acquisition import aq_parent, aq_inner
from AccessControl import ClassSecurityInfo
from App.class_init import default__class_init__ as InitializeClass
from Interface.Implements import flattenInterfaces

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.utils import classImplements, implementedBy
from Products.PluggableAuthService.permissions import ManageUsers

class BasePlugin(SimpleItem, PropertyManager):

    """ Base class for all PluggableAuthService Plugins
    """

    security = ClassSecurityInfo()

    manage_options = ( ( { 'label': 'Activate',
                           'action': 'manage_activateInterfacesForm', }
                         ,
                       )
                     + SimpleItem.manage_options
                     + PropertyManager.manage_options
                     )

    prefix = ''

    _properties = (
        dict(id='prefix', type='string', mode='w',
             label='Optional Prefix'),)

    security.declareProtected( ManageUsers, 'manage_activateInterfacesForm' )
    manage_activateInterfacesForm = PageTemplateFile(
        'www/bpActivateInterfaces', globals(),
        __name__='manage_activateInterfacesForm')

    security.declareProtected( ManageUsers, 'listInterfaces' )
    def listInterfaces( self ):
        """ For ZMI update of interfaces. """

        results = []

        for iface in flattenInterfaces( self.__implements__ ):
            results.append( iface.__name__ )

        return results

    security.declareProtected( ManageUsers, 'testImplements' )
    def testImplements( self, interface ):
        """ Can't access Interface.isImplementedBy() directly in ZPT. """
        return interface.isImplementedBy( self )

    security.declareProtected( ManageUsers, 'manage_activateInterfaces' )
    def manage_activateInterfaces( self, interfaces, RESPONSE=None ):
        """ For ZMI update of active interfaces. """

        pas_instance = self._getPAS()
        plugins = pas_instance._getOb( 'plugins' )

        active_interfaces = []

        for iface_name in interfaces:
            active_interfaces.append( plugins._getInterfaceFromName(
                                                iface_name ) )

        pt = plugins._plugin_types
        id = self.getId()

        for type in pt:
            ids = plugins.listPluginIds( type )
            if id not in ids and type in active_interfaces:
                plugins.activatePlugin( type, id ) # turn us on
            elif id in ids and type not in active_interfaces:
                plugins.deactivatePlugin( type, id ) # turn us off

        if RESPONSE is not None:
            RESPONSE.redirect('%s/manage_workspace'
                              '?manage_tabs_message='
                              'Interface+activations+updated.'
                            % self.absolute_url())

    security.declarePrivate( '_getPAS' )
    def _getPAS( self ):
        """ Canonical way to get at the PAS instance from a plugin """
        return aq_parent( aq_inner( self ) )

try:
    from Products.Five.bridge import fromZ2Interface
except ImportError:
    BasePlugin.__implements__ = SimpleItem.__implements__
else:
    classImplements( BasePlugin
                   , *implementedBy(SimpleItem)
                   )

InitializeClass(BasePlugin)
