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

import httplib
import base64
import json

class Auth0Callback(BrowserView):
    """
    Auth0 redirects to this callback after a login attempt.

    The token is in the window.location.hash and the browser only seems to make
    it visible to us when the redirected response is resolved.
    """
    def __call__(self):
        # TODO: figure out if it's better to use the Auth0 code flow
        # req = self.request
        # resp = req['RESPONSE']
        # code = getQueryArgs(req).get('code', '')
        #
        # data = "{\"grant_type\":\"authorization_code\",\"client_id\": \"cTxVLXKTNloQv1GN9CSRAds5C4PpTkac\",\"client_secret\": \"eh2qKYqug176yr44l647ugkkyzonfWfXGSjMn2h4kP8_EbNv6L1xvMDFUUNTd_ql\",\"code\": \"%s\",\"redirect_uri\": \"https://zenoss5.zenoss-1423-ld/zport/callback\"}" % code
        # headers = {"content-type": "application/json"}
        # conn = httplib.HTTPSConnection("zenoss-dev.auth0.com")
        # conn.request('POST', '/oauth/token', data, headers)
        # response = conn.getresponse()
        # data = response.read()
        # print "AUTH0 CALLBACK DATA:\n%s" % data
        # return data

        zenoss_uri = getZenossURI(self.request)
        # if there is no Auth0 config, not sure how we got here, but redirect
        #  to dmd page... I guess
        conf = getAuth0Conf()
        if not conf:
            return self.request.response.redirect(zenoss_uri + '/zport/dmd')

        # sanitize tenant to get auth0 domain
        domain = conf['tenant'].replace('https://', '').replace('/', '')
        nonce = self.request.get(Auth0.nonce_cookie)
        state = self.request.get(Auth0.state_cookie)
        state_obj = base64.urlsafe_b64decode(state)
        came_from = json.loads(state_obj).get('came_from') or zenoss_uri + '/zport/dmd'
        return """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>ZING Auth</title>
  </head>
  <body>
  <script src="https://cdn.auth0.com/js/auth0/8.12.1/auth0.min.js"></script>
  <script>
    new auth0.WebAuth({
            domain: "%s",
            clientID: "%s"
        }).parseHash({nonce: "%s", state: "%s"}, function (err, authResult)  {
            console.log("AUTH RESULT", authResult);
            if (authResult && authResult.accessToken && authResult.idToken) {
                console.log(authResult);
                window.location ="%s/zport/Auth0Login?idToken="+authResult.idToken+"&came_from=%s";
            } else if(err){
                console.error(err);
            } else {
                let err = {
                    error: "Missing or invalid auth result"
                }
                console.error(err);
            }
        })
  </script>
  </body>
</html>
""" % (domain, conf['clientid'], nonce, state, zenoss_uri, came_from)

class Auth0Login(BrowserView):
    """
    """
    def __call__(self):
        query_args = getQueryArgsFromRequest(self.request)
        token = query_args.get('idToken')
        came_from = query_args.get('came_from')
        if not token:
            self.request.response.setStatus(401)
            self.request.response.write("Missing Id Token")
            return self.request.response

        self.request.response.setCookie(Auth0.cookie_name, token, secure=True, http_only=True)
        return self.request.response.redirect(came_from or getZenossURI(self.request) + '/zport/dmd')
