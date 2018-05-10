##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from Products.Five.browser import BrowserView
from Products.ZenUtils.Auth0 import Auth0, getAuth0Conf
from Products.ZenUtils.CSEUtils import getZenossURI

import logging

log = logging.getLogger('Auth0')

class Auth0Logout(BrowserView):
    """
    Performs a CZ logout, clearing session data for Auth0.  Called from ZC
    when one of the logout links are clicked.
    """
    def __call__(self):
        log.debug('Remotely logged out of CZ using Auth0Logout endpoint')
        request = self.request
        response = request.RESPONSE
        session = request.SESSION
        response.expireCookie("_ZopeId", path='/zport')
        response.expireCookie("beaker.session", path='/')
        response.expireCookie("ZAuthToken", path='/')
        response.expireCookie(Auth0.cookie_key, path='/')
        session.clear()
        # Log out of Auth0 so we aren't automatically reauthed.
        conf = getAuth0Conf()
        if conf:
            log.info('Redirecting user to Auth0 logout')
            response.redirect('%sv2/logout?' % conf['tenant'] +
                              'client_id=%s&' % conf['clientid'] +
                              'returnTo=%s/zport/dmd' % getZenossURI(request),
                              lock=True)
