##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json

from Products.Five.browser import BrowserView

class Login(BrowserView):
    """
    """

    def __call__(self, *args, **kwargs):
        """
          extract login/password credentials, test authentication, and create a token
        """

        #The session_folder auto clears data objects -
        #  http://docs.zope.org/zope2/zope2book/Sessions.html
        #self.context.clearExpiredTokens()

        credentials = self.context.extractCredentials(self.request)

        login = credentials.get('login', None)
        password = credentials.get('password', None)

        # no credentials to test authentication
        if login is None or password is None:
            self.request.response.setStatus(401)
            return

        # test authentication
        if not self.context.authenticateCredentials(login, password):
            self.request.response.setStatus(401)
            return

        # successful authentication
        session = self.request.get('SESSION')
        tokenId = self.context.getTokenId()

        # create the session data
        token = self.context.createToken(session.id, tokenId)

        return json.dumps(token)


class Validate(BrowserView):
    """
      assert token id exists in session data and token id hasn't expired
    """

    def __call__(self, *args, **kwargs):
        """
            extract token id, test token expiration, and return token
        """
        tokenId = self.request.get('id', None)
        if tokenId is None:
            tokenId = self.request.getHeader('X-ZAuth-Token')
            
        # missing token id
        if tokenId is None:
            self.request.response.setStatus(401)
            return

        #grab token to handle edge case, when expiration happens after expiration test
        token = self.context.getToken(tokenId)
        tokenId = tokenId.strip('"')
        if self.context.tokenExpired(tokenId):
            self.request.response.setStatus(401)
            return

        return json.dumps(token)
