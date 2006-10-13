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
""" Classes: LocalRolePlugin

$Id: LocalRolePlugin.py 40169 2005-11-16 20:09:11Z tseaver $
"""
from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins import IRolesPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class ILocalRolePlugin(Interface):
    """ Marker interface.
    """

manage_addLocalRolePluginForm = PageTemplateFile(
    'www/lrpAdd', globals(), __name__='manage_addLocalRolePluginForm' )

def addLocalRolePlugin( dispatcher, id, title='', RESPONSE=None ):
    """ Add a Local Role Plugin to 'dispatcher'.
    """

    lrp = LocalRolePlugin( id, title )
    dispatcher._setObject( id, lrp )

    if RESPONSE is not None:
        RESPONSE.redirect( '%s/manage_main?manage_tabs_message=%s' %
                           ( dispatcher.absolute_url()
                           , 'LocalRolePlugin+added.' ) )

class LocalRolePlugin( BasePlugin ):
    """ Provide roles during Authentication from local roles
        assignments made on the root object.
    """

    meta_type = 'Local Role Plugin'
    security = ClassSecurityInfo()

    def __init__( self, id, title=None ):
        self._setId( id )
        self.title = title

    #
    #    IRolesPlugin implementation
    #
    security.declarePrivate( 'getRolesForPrincipal' )
    def getRolesForPrincipal( self, principal, request=None ):

        """ See IRolesPlugin.
        """
        local_roles = getattr( self.getPhysicalRoot()
                             , '__ac_local_roles__'
                             , None )
        if local_roles is None:
            return None
        return local_roles.get( principal.getId() )

classImplements( LocalRolePlugin
               , ILocalRolePlugin
               , IRolesPlugin
               )

InitializeClass( LocalRolePlugin )
