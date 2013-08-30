##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from zope.interface import implements
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from ZenModelRM import ZenModelRM
from Products.PluggableAuthService import interfaces
from .interfaces import IAuthorization

import time


def manage_addAuthorization(context):
    """
    Add a new authorization object.
    """
    #import pprint; pprint.pprint( dir( context))

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

    def setCookie(self):
        """
        Set the ZAuth cookie so ajax requests will be authorized
        """
        self.REQUEST.response.setCookie('ZAuthToken', self.REQUEST.SESSION.id, path="/")

    def createToken(self, sessionId, tokenId, expires):
        """
        @param sessionId:
        @return:
        """
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

        if token['expires'] <= time.time():
            del self.temp_folder.session_data[sessionId]
            return True

        return False


    def clearExpiredTokens(self):
        to_delete = []
        for (key, value) in self.temp_folder.session_data.items():
            if isinstance( value, dict) and 'expires' in value:
                if time.time() <= time.time():
                    to_delete.append( key)

        for key in to_delete:
            del self.temp_folder.session_data[ key]

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
