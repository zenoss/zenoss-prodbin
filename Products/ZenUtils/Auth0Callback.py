##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from Products.Five.browser import BrowserView
from .Auth0 import AUTH0_CLIENT_ID

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
                console.log(authResult.idToken);
                window.location ="https://zenoss5.zenoss-1423-ld/zport/dmd?idToken="+authResult.idToken;
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
""" % ("zenoss-dev.auth0.com", AUTH0_CLIENT_ID)
