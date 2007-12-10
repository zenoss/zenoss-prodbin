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
""" SearchPrincipalsPlugin   Plugin to delegate enumerateUsers
                             and enumerateGroups requests to another 
                             PluggableAuthService
"""

# General Python imports
import copy, os
from urllib import quote_plus

# Zope imports
from Acquisition import aq_base
from OFS.Folder import Folder
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.SpecialUsers import emergency_user
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins import \
     IUserEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import \
     IGroupEnumerationPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class ISearchPrincipalsPlugin(Interface):
    """ Marker interface.
    """

addSearchPrincipalsPluginForm = PageTemplateFile(
    'www/sppAdd', globals(), __name__='addSearchPrincipalsPluginForm' )


def addSearchPrincipalsPlugin( dispatcher
                             , id
                             , title=''
                             , delegate_path=''
                             , REQUEST=None
                             ):
    """ Factory method to instantiate a SearchPrincipalsPlugin """
    spp = SearchPrincipalsPlugin( id, title=title
                                , delegate_path=delegate_path )
    dispatcher._setObject(id, spp)

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect('%s/manage_main' % dispatcher.absolute_url())


class SearchPrincipalsPlugin(BasePlugin):
    """ SearchPrincipalsPlugin delegates its enumerateUsers
    and enumerateGroups methods to a delegate object
    """
    security = ClassSecurityInfo()
    meta_type = 'Search Principals Plugin'

    _properties = ( { 'id' : 'delegate'
                    , 'label' : ' Delegate Path'
                    , 'type' : 'string'
                    , 'mode' : 'w'
                    }
                  ,
                  )

    def __init__(self, id, title='', delegate_path=''):
        """ Initialize a new instance """
        self.id = id
        self.title = title
        self.delegate = delegate_path

    security.declarePrivate('_getDelegate')
    def _getDelegate(self):
        """ Safely retrieve a PluggableAuthService to work with """
        uf = getattr(aq_base(self), 'acl_users', None)

        if uf is None and self.delegate:
            uf = self.unrestrictedTraverse(self.delegate)

        return uf

    security.declarePrivate('enumerateUsers')
    def enumerateUsers( self
                      , id=None
                      , login=None
                      , exact_match=0
                      , sort_by=None
                      , max_results=None
                      , **kw
                      ):
        """ see IUserEnumerationPlugin """
        acl = self._getDelegate()

        if acl is None:
            return ()

        return acl.searchUsers( id=id
                              , login=login
                              , exact_match=exact_match
                              , sort_by=sort_by
                              , max_results=max_results
                              , **kw )

    security.declarePrivate('enumerateGroups')
    def enumerateGroups( self
                       , id=None
                       , exact_match=0
                       , sort_by=None
                       , max_results=None
                       , **kw
                       ):
        """ see IGroupEnumerationPlugin """
        acl = self._getDelegate()

        if acl is None:
            return ()

        return acl.searchGroups( id=id
                               , exact_match=exact_match
                               , sort_by=sort_by
                               , max_results=max_results
                               , **kw )

classImplements( SearchPrincipalsPlugin
               , ISearchPrincipalsPlugin
               , IUserEnumerationPlugin
               , IGroupEnumerationPlugin
               )

InitializeClass(SearchPrincipalsPlugin)
