##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import time

from Products.Five.browser import BrowserView
from Products.PluggableAuthService import interfaces


class Login(BrowserView):
    """
    """

    def __call__(self, *args, **kwargs):
        """
          extract login/password credentials, test authentication, and create a token
        """

        self.context.clearExpiredTokens()

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
        session = self.request.get('SESSION', None)
        tokenId = session.id
        expires = time.time() + 10 * 60

        # create the session data
        token = self.context.createToken(session.id, tokenId, expires)
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

        # missing token id
        if tokenId is None:
            self.request.response.setStatus(401)
            return

        # tokenId == sessionId
        if self.context.tokenExpired(tokenId):
            self.request.response.setStatus(401)
            return

        token = self.context.getToken(tokenId)
        return json.dumps(token)
