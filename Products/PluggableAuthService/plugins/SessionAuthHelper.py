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
""" Class: SessionAuthHelper

$Id: SessionAuthHelper.py 40169 2005-11-16 20:09:11Z tseaver $
"""

from AccessControl.SecurityInfo import ClassSecurityInfo
from App.class_init import default__class_init__ as InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins import \
        ILoginPasswordHostExtractionPlugin
from Products.PluggableAuthService.interfaces.plugins import \
        ICredentialsUpdatePlugin
from Products.PluggableAuthService.interfaces.plugins import \
        ICredentialsResetPlugin
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.PluggableAuthService.utils import Interface

class ISessionAuthHelper(Interface):
    """ Marker interface.
    """


manage_addSessionAuthHelperForm = PageTemplateFile(
    'www/saAdd', globals(), __name__='manage_addSessionAuthHelperForm')


def manage_addSessionAuthHelper(dispatcher, id, title=None, REQUEST=None):
    """ Add a Session Auth Helper to a Pluggable Auth Service. """
    sp = SessionAuthHelper(id, title)
    dispatcher._setObject(sp.getId(), sp)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect( '%s/manage_workspace'
                                      '?manage_tabs_message='
                                      'SessionAuthHelper+added.'
                                    % dispatcher.absolute_url() )


class SessionAuthHelper(BasePlugin):
    """ Multi-plugin for managing details of Session Authentication. """
    meta_type = 'Session Auth Helper'
    security = ClassSecurityInfo()


    def __init__(self, id, title=None):
        self._setId(id)
        self.title = title

    security.declarePrivate('extractCredentials')
    def extractCredentials(self, request):
        """ Extract basic auth credentials from 'request'. """
        creds = {}

        # Looking into the session first...
        name = request.SESSION.get('__ac_name', '')
        password = request.SESSION.get('__ac_password', '')

        if name:
            creds[ 'login' ] = name
            creds[ 'password' ] = password
        else:
            # Look into the request now
            login_pw = request._authUserPW()

            if login_pw is not None:
                name, password = login_pw
                creds[ 'login' ] = name
                creds[ 'password' ] = password
                request.SESSION.set('__ac_name', name)
                request.SESSION.set('__ac_password', password)

        if creds:
            creds['remote_host'] = request.get('REMOTE_HOST', '')

            try:
                creds['remote_address'] = request.getClientAddr()
            except AttributeError:
                creds['remote_address'] = request.get('REMOTE_ADDR', '')

        return creds

    security.declarePrivate('updateCredentials')
    def updateCredentials(self, request, response, login, new_password):
        """ Respond to change of credentials. """
        request.SESSION.set('__ac_name', login)
        request.SESSION.set('__ac_password', new_password)

    security.declarePrivate('resetCredentials')
    def resetCredentials(self, request, response):
        """ Empty out the currently-stored session values """
        request.SESSION.set('__ac_name', '')
        request.SESSION.set('__ac_password', '')

classImplements( SessionAuthHelper
               , ISessionAuthHelper
               , ILoginPasswordHostExtractionPlugin
               , ICredentialsUpdatePlugin
               , ICredentialsResetPlugin
               )

InitializeClass(SessionAuthHelper)

