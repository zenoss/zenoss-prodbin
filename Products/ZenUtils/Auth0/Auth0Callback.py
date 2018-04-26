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
from Products.ZenUtils.CSEUtils import getZenossURI, getCSEConf
from Products.ZenUtils.Utils import getQueryArgsFromRequest

import base64
import httplib
import json
import logging
import urllib

log = logging.getLogger('Auth0')

class Auth0Callback(BrowserView):
    """
    Auth0 redirects to this callback after a login attempt.
    """
    def __call__(self):
        zport_dmd = '/zport/dmd'
        conf = getAuth0Conf()
        zenoss_uri = getZenossURI(self.request)
        if not conf:
            log.warn('No Auth0 config in GlobalConfig - not saving id token')
            return self.request.response.redirect(zenoss_uri + zport_dmd)

        args = getQueryArgsFromRequest(self.request)
        state_arg = args.get('state')
        code = args.get('code')
        error = args.get('error', None)

        if error:
            log.debug('Auth0 error response: {}'.format(error))

        domain = conf['tenant'].replace('https://', '').replace('/', '')

        if error:
            # We need to make a new request to authorize without the
            # prompt parameter so that auth0 presents a login screen.
            uri = "%sauthorize?" % conf['tenant'] + \
                  "response_type=code&" + \
                  "client_id=%s&" % conf['clientid'] + \
                  "state=%s&" % state_arg + \
                  "scope=openid offline_access&" + \
                  "redirect_uri=%s/zport/Auth0Callback" % zenoss_uri
            return self.request.response.redirect(uri)
        else:
            data = {
                "grant_type": "authorization_code",
                "client_id": conf['clientid'],
                "client_secret": conf['client-secret'],
                "code": code,
                "audience": "%s/userinfo" % domain,
                "scope": "openid profile",
                "redirect_uri": "%s/zport/Auth0Callback" % zenoss_uri
            }

            conn = httplib.HTTPSConnection(domain)
            headers = {"content-type": "application/json"}
            try:
                conn.request('POST', '/oauth/token', json.dumps(data), headers)
                resp_string = conn.getresponse().read()
            except Exception as a:
                log.error('Unable to obtain token from Auth0: %s', a)
                return self.request.response.redirect(zenoss_uri + zport_dmd)

            resp_data = json.loads(resp_string)
            refresh_token = resp_data.get('refresh_token')
            id_token = resp_data.get('id_token')

            Auth0.storeIdToken(id_token, self.request.SESSION, conf, refresh_token)

            came_from = json.loads(base64.b64decode(urllib.unquote(state_arg)))['came_from']
            virtual_root = getCSEConf().get('virtualroot', '')
            if virtual_root and \
                virtual_root not in came_from \
                and zport_dmd in came_from:
                came_from = came_from.replace(zport_dmd, virtual_root + zport_dmd)
            return self.request.response.redirect(came_from)
