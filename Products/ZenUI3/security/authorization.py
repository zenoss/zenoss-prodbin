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
        """

        type = interfaces.plugins.IExtractionPlugin
        plugins = self.context.zport.acl_users.plugins.listPlugins(type)

        login = None
        password = None

        # look in the extraction plugins for the credentials
        for (extractor_id, extractor) in plugins:
            creds = extractor.extractCredentials(self.request)
            if 'login' in creds and 'password' in creds:
                login = creds['login']
                password = creds['password']
                break

        # look in the request headers for the creds
        if login is None or password is None:
            login = self.request.get('login', None)
            password = self.request.get('password', None)

        # no credentials to test authentication
        if login is None or password is None:
            self.request.response.setStatus(401)
            return

        # test authentication
        if not self.authenticate(login, password):
            self.request.response.setStatus(401)
            return

        # successful authentication
        session = self.request.get('SESSION', None)
        token_id = session.id
        expires = time.time() + 10 * 60

        # create the session data
        session_data = dict(id=token_id, expires=expires)
        self.context.temp_folder.session_data[token_id] = session_data
        return json.dumps(session_data)


    def authenticate(self, login, password):
        return self.context.zport.dmd.ZenUsers.authenticateCredentials(login, password)


class Validate(BrowserView):
    """
      assert token id exists in session data and token id hasn't expired
    """

    def __call__(self, *args, **kwargs):
        """
        """

        token_id = self.request.get('id', None)

        # missing token id
        if token_id is None:
            self.request.response.setStatus(401)
            return

        session_data = self.context.temp_folder.session_data.get(token_id, None)

        # missing session data
        if session_data is None:
            self.request.response.setStatus(401)
            return

        # test expiration
        expires = session_data.get('expires', None)
        if expires is None or time.time() >= expires:
            self.request.response.setStatus(401)
            return

        return json.dumps(session_data)
