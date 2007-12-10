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
""" DelegatingMultiPlugin   Shim to use any User Folder with the
                            PluggableAuthenticationService
"""

__doc__     = """ Delegating User Folder shim module """
__version__ = '$Revision: 40169 $'[11:-2]

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
    IAuthenticationPlugin
from Products.PluggableAuthService.interfaces.plugins import \
    IUserEnumerationPlugin
from Products.PluggableAuthService.interfaces.plugins import \
    IRolesPlugin
from Products.PluggableAuthService.interfaces.plugins import \
    ICredentialsUpdatePlugin
from Products.PluggableAuthService.interfaces.plugins import \
    ICredentialsResetPlugin
from Products.PluggableAuthService.interfaces.plugins import \
    IPropertiesPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class IDelegatingMultiPlugin(Interface):
    """ Marker interface.
    """

manage_addDelegatingMultiPluginForm = PageTemplateFile(
    'www/dmpAdd', globals(), __name__='manage_addDelegatingMultiPluginForm' )


def manage_addDelegatingMultiPlugin( self
                                   , id
                                   , title=''
                                   , delegate_path=''
                                   , REQUEST=None
                                   ):
    """ Factory method to instantiate a DelegatingMultiPlugin """
    # Make sure we really are working in our container (the 
    # PluggableAuthService object)
    self = self.this()

    # Instantiate the folderish adapter object
    lmp = DelegatingMultiPlugin( id, title=title
                               , delegate_path=delegate_path )
    self._setObject(id, lmp)

    if REQUEST is not None:
        REQUEST.RESPONSE.redirect('%s/manage_main' % self.absolute_url())



class DelegatingMultiPlugin(Folder, BasePlugin):
    """ The adapter that mediates between the PAS and the DelegatingUserFolder
    """
    security = ClassSecurityInfo()
    meta_type = 'Delegating Multi Plugin'

    manage_options = ( BasePlugin.manage_options[:1]
                     + Folder.manage_options
                     )

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


    security.declarePrivate('_getUserFolder')
    def _getUserFolder(self):
        """ Safely retrieve a User Folder to work with """
        uf = getattr(aq_base(self), 'acl_users', None)

        if uf is None and self.delegate:
            uf = self.unrestrictedTraverse(self.delegate)

        return uf


    security.declarePrivate('authenticateCredentials')
    def authenticateCredentials(self, credentials):
        """ Fulfill AuthenticationPlugin requirements """
        acl = self._getUserFolder()
        login = credentials.get('login', '')
        password = credentials.get('password', '')

        if not acl or not login or not password:
            return (None, None)

        if login == emergency_user.getUserName():
            return ( login, login )

        user = acl.getUser(login)
        if user is None:
            return (None, None)
        elif user and user._getPassword() == password:
            return ( user.getId(), login )
            
        return (None, None)


    security.declarePrivate('updateCredentials')
    def updateCredentials(self, request, response, login, new_password):
        """ Fulfill CredentialsUpdatePlugin requirements """
        # Need to at least remove user from cache
        pass


    security.declarePrivate('resetCredentials')
    def resetCredentials(self, request, response):
        """ Fulfill CredentialsResetPlugin requirements """
        # Remove user from cache?
        pass


    security.declarePrivate('getPropertiesForUser')
    def getPropertiesForUser(self, user, request=None):
        """ Fullfill PropertiesPlugin requirements """
        acl = self._getUserFolder()

        if acl is None:
            return {}

        user = acl.getUserById(user.getId())

        if user is None:
            return {}

        # XXX WAAA
        return copy.deepcopy(user.__dict__)


    security.declarePrivate('getRolesForPrincipal')
    def getRolesForPrincipal(self, user, request=None):
        """ Fullfill RolesPlugin requirements """
        acl = self._getUserFolder()

        if acl is None:
            return ()

        user = acl.getUserById(user.getId())

        if user is None:
            return ()

        return tuple(user.getRoles())


    security.declarePrivate('enumerateUsers')
    def enumerateUsers( self
                      , id=None
                      , login=None
                      , exact_match=0
                      , sort_by=None
                      , max_results=None
                      , **kw
                      ):
        """ Fulfill the EnumerationPlugin requirements """
        result = []
        acl = self._getUserFolder()
        plugin_id = self.getId()
        edit_url = '%s/%s/manage_userrecords' % (plugin_id, acl.getId())

        if acl is None:
            return ()

        if exact_match:
            if id:
                user = acl.getUserById(id)
            elif login:
                user = acl.getUser(login)
            else:
                msg = 'Exact Match specified but no ID or Login given'
                raise ValueError, msg

            if user is not None:
                result.append( { 'id' : user.getId()
                               , 'login' : user.getUserName()
                               , 'pluginid' : plugin_id
                               , 'editurl' : '%s' % edit_url
                               } ) 
        else:
            l_results = []
            seen = []
            # XXX WAAAAA!!!!
            all_users = acl.getUsers()

            for user in all_users:
                if id:
                    if user.getId().find(id) != -1:
                        result.append( { 'login' : user.getUserName()
                                       , 'id' : user.getId()
                                       , 'pluginid' : plugin_id
                                       } )
                elif login:
                    if user.getUserName().find(login) != -1:
                        result.append( { 'login' : user.getUserName()
                                       , 'id' : user.getId()
                                       , 'pluginid' : plugin_id
                                       } )

            if sort_by is not None:
                result.sort(lambda a, b: cmp( a.get(sort_by, '').lower()
                                            , b.get(sort_by, '').lower()
                                            ) )

            if max_results is not None:
                try:
                    max_results = int(max_results)
                    result = result[:max_results+1]
                except ValueError:
                    pass

        return tuple(result)

classImplements( DelegatingMultiPlugin
               , IDelegatingMultiPlugin
               , IAuthenticationPlugin
               , IUserEnumerationPlugin
               , IRolesPlugin
               , ICredentialsUpdatePlugin
               , ICredentialsResetPlugin
               , IPropertiesPlugin
               )


InitializeClass(DelegatingMultiPlugin)
