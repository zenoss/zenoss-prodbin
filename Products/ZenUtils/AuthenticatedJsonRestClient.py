##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import base64
from zenoss.protocols.services import JsonRestServiceClient
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration


class AuthenticatedJsonRestClient(JsonRestServiceClient):
    """
    Json Rest Client that supplies basic authorization for all requests.
    If the credentials are not supplied in the constructor the zauth-username
    and zauth-password from global.conf is used.
    """
    def __init__(self, uri, username=None, password=None, **kwargs):
        if not username: 
            username = getGlobalConfiguration().get('zauth-username', None)
        if not password:
            password = getGlobalConfiguration().get('zauth-password', None)

        # make sure a username was set
        if not username:
            raise Exception("Missing global.conf zauth-username")
        auth = base64.b64encode('%s:%s' %(username, password))
        super(AuthenticatedJsonRestClient, self).__init__(uri, **kwargs)
        self._default_headers = {
            'Authorization' : 'basic %s' % auth
        }

