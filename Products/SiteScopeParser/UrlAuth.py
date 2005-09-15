#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

"""UrlAuth

Open URL with basic authentication

$Id: UrlAuth.py,v 1.2 2002/05/01 20:01:02 alex Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]

import urllib

from Products.ZenUtils import ZentinelException

class AuthError(ZentinelException): pass

class UrlAuth(urllib.FancyURLopener):
    
    def __init__(self, user = "", password = ""):
        self._user = user
        self._password = password
        urllib.FancyURLopener.__init__(self)

    def prompt_user_passwd(self, host, realm):
        return (self._user, self._password)

    def retry_http_basic_auth(self, url, realm, data=None):
        raise AuthError
        
