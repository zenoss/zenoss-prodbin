##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from Products.Five.browser import BrowserView
from .Auth0 import getAuth0Conf, getZenossURI, getQueryArgs
import httplib

class Auth0Callback(BrowserView):
    """
    Auth0 redirects to this callback after a login attempt.

    The token is in the window.location.hash and the browser only seems to make
    it visible to us when the redirected response is resolved.

    TODO:
    - Find out how we can get the user back to the page they originally tried
      to hit, currently just using https://zenoss5.zenoss-1423-ld/zport/dmd,
      but may be able to pass that through with "state" arg to Auth0
    - Share nonce between Auth0 PAS plugin and here
    - Read in Domain and Client ID from config
    """
    def __call__(self):
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
        conf = getAuth0Conf()

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
        }).parseHash({nonce: "abcd1234"}, function (err, authResult)  {
            console.log("AUTH RESULT", authResult);
            if (authResult && authResult.accessToken && authResult.idToken) {
                console.log(authResult);
                window.location ="%s/zport/Auth0Login?idToken="+authResult.idToken;
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
""" % (conf['tenant'].replace('https://', '').replace('/', ''), conf['clientid'], getZenossURI(self.request))

class Auth0Login(BrowserView):
    """
    """
    cookieName = '__macaroon'
    def __call__(self):
        query_args = getQueryArgs(self.request)
        token = query_args.get('idToken', None)
        came_from = query_args.get('came_from', '')
        if token is None:
            self.request.response.setStatus(401)
            self.request.response.write( "Missing Id Token")

        self.request.response.setCookie(self.cookieName, token)
        return self.request.response.redirect(came_from or getZenossURI(self.request) + '/zport/dmd')
