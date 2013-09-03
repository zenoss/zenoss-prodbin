##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from App.config import getConfiguration
from zope.interface import implements
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from ZenModelRM import ZenModelRM
from Products.PluggableAuthService import interfaces
from .interfaces import IAuthorization

import time

try:
    _SESSION_TIMEOUT_SECONDS = 60 * getConfiguration().session_timeout_minutes
except AttributeError:
    # we may not always have access to zope.conf so make a default session timeout
    _SESSION_TIMEOUT_SECONDS = 3600 * 20


def manage_addAuthorization(context):
    """
    Add a new authorization object.
    """
    try:
        context.authorization
    except AttributeError, ex:
        authorization = Authorization('authorization')
        context._setObject(authorization.getId(), authorization)


class Authorization(ZenModelRM):
    """
    """
    implements(IAuthorization)

    meta_type = 'Authorization'
    security = ClassSecurityInfo()

    def __init__(self, id):
        ZenModelRM.__init__(self, id);

    def getTokenId(self):
        return self.REQUEST.SESSION.id

    def setCookie(self):
        """
        Set the ZAuth cookie so ajax requests will be authorized
        """
        self.REQUEST.response.setCookie('ZAuthToken', self.REQUEST.SESSION.id, path="/")
        token = self.getTokenId()
        self.createToken(token, token)

    def createToken(self, sessionId, tokenId, expires=None):
        """
        @param sessionId:
        @return:
        """
        if expires is None:
          expires = time.time() + _SESSION_TIMEOUT_SECONDS

        token = dict(id=tokenId, expires=expires)
        self.temp_folder.session_data[sessionId] = token
        return token

    def getToken(self, sessionId):
        """
        @param sessionId:
        @return:
        """
        return self.temp_folder.session_data.get(sessionId, None)

    def tokenExpired(self, sessionId):
        token = self.getToken(sessionId)
        if token is None:
            return True

        return time.time() >= token['expires']

    def extractCredentials(self, request):
        type = interfaces.plugins.IExtractionPlugin
        plugins = self.zport.acl_users.plugins.listPlugins(type)

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
        return self.zport.dmd.ZenUsers.authenticateCredentials(login, password)


InitializeClass(Authorization)
