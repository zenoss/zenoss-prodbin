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
from Products.ZenUtils.Utils import getQueryArgsFromRequest

import base64
import httplib
import json
import urllib

class Auth0Callback(BrowserView):
    """
    Auth0 redirects to this callback after a login attempt.
    """
    def __call__(self):
        conf = getAuth0Conf()
        zenoss_uri = getZenossURI(self.request)
        if not conf:
            return self.request.response.redirect(zenoss_uri + '/zport/dmd')

        args = getQueryArgsFromRequest(self.request)
        state_arg = args.get('state')
        code = args.get('code')

        domain = conf['tenant'].replace('https://', '').replace('/', '')

        data = {
            "grant_type": "authorization_code",
            "client_id": conf['clientid'],
            "client_secret": conf['client-secret'],
            "code": code,
            "audience": "%s/userinfo" % domain,
            "scope": "openid profile",
            "redirect_uri": "%s/zport/Auth0Callback" % zenoss_uri
        }

        resp_string = ''
        conn = httplib.HTTPSConnection(domain)
        headers = {"content-type": "application/json"}
        try:
            conn.request('POST', '/oauth/token', json.dumps(data), headers)
            resp_string = conn.getresponse().read()
        except:
            # can we handle this better?
            return self.request.response.redirect(zenoss_uri + '/zport/dmd')

        # all the stuff we should get back
        # TODO: do something with these
        resp_data = json.loads(resp_string)
        access_token = resp_data.get('access_token')
        refresh_token = resp_data.get('refresh_token')
        id_token = resp_data.get('id_token')
        expires_in = resp_data.get('expires_in')
        token_type = resp_data.get('token_type')

        came_from = json.loads(base64.b64decode(urllib.unquote(state_arg)))['came_from']

        self.request.response.setCookie(Auth0.cookie_name, id_token, secure=True, http_only=True)
        return self.request.response.redirect(came_from)
