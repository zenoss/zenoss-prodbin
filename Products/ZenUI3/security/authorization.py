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
from Products.Zuul.utils import createAuthToken


ZAUTH_HEADER_ID = 'X-ZAuth-Token'


class Authorization(BrowserView):
    """
    This view acts as a namespace so the client requests are /authorization/login and
    /authorization/validate
    """
    def __getitem__(self, index):
        if index == "login":
            return Login(self.context, self.request)
        if index == "validate":
            return Validate(self.context, self.request)
        raise Exception("Invalid authorization view %s" % index)

class Login(BrowserView):
    """
    Validates the credentials supplied and creates a new authorization token.
    """
    def extractCredentials(self, request):
        type = interfaces.plugins.IExtractionPlugin
        plugins = self.context.context.zport.acl_users.plugins.listPlugins(type)

        # look in the extraction plugins for the credentials
        for (extractor_id, extractor) in plugins:
            creds = extractor.extractCredentials(request)
            if 'login' in creds and 'password' in creds:
                return creds

        # look in the request headers for the creds
        login = request.get('login', None)
        password = request.get('password', None)
        return {'login': login, 'password': password}

    def authenticateCredentials(self, login, password):
        return self.context.context.zport.dmd.ZenUsers.authenticateCredentials(login, password)

    def __call__(self, *args, **kwargs):
        """
        Extract login/password credentials, test authentication, and create a token
        """

        #The session_folder auto clears data objects -
        #  http://docs.zope.org/zope2/zope2book/Sessions.html
        #self.context.clearExpiredTokens()
        credentials = self.extractCredentials(self.request)

        login = credentials.get('login', None)
        password = credentials.get('password', None)

        # no credentials to test authentication
        if login is None or password is None:
            self.request.response.setStatus(401)
            return

        # test authentication
        if not self.authenticateCredentials(login, password):
            self.request.response.setStatus(401)
            return

        # create the session data
        token = createAuthToken(self.request, self.context.context.zport.dmd)

        return json.dumps(token)


class Validate(BrowserView):
    """
    Assert token id exists in session data and token id hasn't expired
    """

    def getToken(self, sessionId):
        """
        @param sessionId:
        @return:
        """
        return self.context.context.temp_folder.session_data.get(sessionId, None)

    def tokenExpired(self, sessionId):
        token = self.getToken(sessionId)
        if token is None:
            return True

        return time.time() >= token['expires']

    def __call__(self, *args, **kwargs):
        """
            extract token id, test token expiration, and return token
        """
        tokenId = self.request.get('id', None)
        if tokenId is None:
            tokenId = self.request.getHeader(ZAUTH_HEADER_ID)

        # missing token id
        if tokenId is None:
            self.request.response.setStatus(401)
            return

        #grab token to handle edge case, when expiration happens after expiration test
        tokenId = tokenId.strip('"')
        token = self.getToken(tokenId)
        if self.tokenExpired(tokenId):
            self.request.response.setStatus(401)
            return

        return json.dumps(token)
