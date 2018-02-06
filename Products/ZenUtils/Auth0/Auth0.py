##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from AccessControl.class_init import InitializeClass
from Products.CMFCore.utils import getToolByName
from Products.PluggableAuthService.interfaces.plugins import (IExtractionPlugin,
                                                            IAuthenticationPlugin,
                                                            IChallengePlugin)
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.ZenUtils.AuthUtils import getJWKS, publicKeysFromJWKS, getBearerToken
from Products.ZenUtils.CSEUtils import getZenossURI
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.PASUtils import activatePluginForInterfaces, movePluginToTop
from Products.ZenUtils.Utils import getQueryArgsFromRequest

import base64
import httplib
import json
import jwt
import logging

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'
PLUGIN_VERSION=1

_AUTH0_CONFIG = {
        'clientid': None,
        'client-secret': None,
        'tenant': None,
        'connection': None
    }

def getAuth0Conf():
    """Return a dictionary containing Auth0 configuration or None
    """
    global _AUTH0_CONFIG
    if _AUTH0_CONFIG is not None and not all(_AUTH0_CONFIG.values()):
        d = {}
        config = getGlobalConfiguration()
        for k in _AUTH0_CONFIG:
            d[k] = config.get('auth0-' + k)
        _AUTH0_CONFIG = d if all(d.values()) else None
    return _AUTH0_CONFIG

def manage_addAuth0(context, id, title=None):
    obj = Auth0(id, title)
    context._setObject(obj.getId(), obj)

def manage_delAuth0(context, id):
    context._delObject(id)

class Auth0(BasePlugin):
    """Auth0 is a PluggableAuthService MultiPlugin which satisfies interfaces:
        IExtractionPlugin
        IAuthenticationPlugin
        IChallengePlugin

    It aims to provide authentication via Auth0, and supports reading tokens
        from a cookie, the Authorization header, or query args
    """

    meta_type = 'Auth0 plugin'
    session_idtoken_name = 'auth0-id-token'
    session_refresh_key = 'auth0-refresh-token'
    cache = {}

    def __init__(self, id, title=None):
        self._id = self.id = id
        self.title = title
        self.version = PLUGIN_VERSION

    @staticmethod
    def _getKey(key_id, conf):
        # Look up a key in the cached list of keys.
        # If we have never looked up a given key, refresh the cache.
        if 'keys' not in Auth0.cache or key_id not in Auth0.cache['keys']:
            jwks = getJWKS(conf['tenant'] + '.well-known/jwks.json')
            Auth0.cache['keys'] = publicKeysFromJWKS(jwks)
        return Auth0.cache['keys'].setdefault(key_id, None)


    def extractCredentials(self, request):
        """extractCredentials satisfies the PluggableAuthService
            IExtractionPlugin interface.
        A successful extraction will return a dict with the 'token' field
            containing a jwt.
        """
        conf = getAuth0Conf()
        if not conf:
            return None

        id_token = request.SESSION.get(Auth0.session_idtoken_name)
        if not id_token:
            return {}

        # get the key id from the jwt header
        key_id = jwt.get_unverified_header(id_token)['kid']
        key = Auth0._getKey(key_id, conf)
        if not key:
            return {}

        try:
            payload = jwt.decode(id_token, key, verify=True,
                                 algorithms=['RS256'],
                                 audience=conf['clientid'],
                                 issuer=conf['tenant'])
        except jwt.ExpiredSignatureError:
            # Token is present but expired, get a new one with refresh token
            refresh_token = request.SESSION.get(Auth0.session_refresh_key)
            if not refresh_token:
                return {}

            data = {
                "grant_type": "refresh_token",
                "client_id": conf['clientid'],
                "client_secret": conf['client-secret'],
                "refresh_token": refresh_token
            }

            conn = httplib.HTTPSConnection(conf['tenant'].replace('https://', ''))
            headers = {"content-type": "application/json"}
            try:
                conn.request('POST', '/oauth/token', json.dumps(data), headers)
                resp_string = conn.getresponse().read()
            except:
                # can we handle this better?
                return {}

            resp_data = json.loads(resp_string)
            id_token = resp_data.get('id_token')

            payload = jwt.decode(id_token, key, verify=True,
                                 algorithms=['RS256'],
                                 audience=conf['clientid'],
                                 issuer=conf['tenant'])
            request.SESSION[Auth0.session_idtoken_name] = id_token
        except:
            # Signature is invalid or some internal problem with jwt.decode
            return {}

        if not payload or 'sub' not in payload:
            return {}

        # Auth0 "sub" format is: connection|user or method|connection|user
        userid = payload['sub'].encode('utf8').split('|')[-1]
        if not userid:
            return {}

        return {'auth0_userid': userid}


    def authenticateCredentials(self, credentials):
        """authenticateCredentials satisfies the PluggableAuthService
            IAuthenticationPlugin interface.
        A successful authentication will return (userid, userid).
        """
        # Ignore credentials that are not from our extractor
        if credentials.get('extractor') != PLUGIN_ID or \
           'auth0_userid' not in credentials:
            return None

        userid = credentials.get('auth0_userid')
        if not userid:
            return None

        return (userid, userid)

    def challenge(self, request, response):
        """challenge satisfies the PluggableAuthService
            IChallengePlugin interface.
        """
        conf = getAuth0Conf()
        if not conf or not all(conf.values()):
            return False

        zenoss_uri = getZenossURI(request)
        # pass state to auth0 so we can redirect user to where they wanted to go
        state_obj = {
            "came_from": request.ACTUAL_URL
        }
        state = base64.urlsafe_b64encode(json.dumps(state_obj))

        request['RESPONSE'].redirect("%sauthorize?" % conf['tenant'] +
                                     "response_type=code&" +
                                     "client_id=%s&" % conf['clientid'] +
                                     "connection=%s&" % conf['connection'] +
                                     "state=%s&" % state +
                                     "scope=openid offline_access&" +
                                     "redirect_uri=%s/zport/Auth0Callback" % zenoss_uri,
                                     lock=1)
        return True


classImplements(Auth0, IAuthenticationPlugin, IExtractionPlugin, IChallengePlugin)

InitializeClass(Auth0)

def setup(context):
    app = context.getPhysicalRoot()
    zport = app.zport
    zport_acl = getToolByName(zport, 'acl_users')

    # Check for existing Auth0 plugin
    existing_auth0 = getattr(zport_acl, PLUGIN_ID, None)
    if existing_auth0:
        version = getattr(existing_auth0, 'version', 0)
        if version == PLUGIN_VERSION:
            # Existing plugin version matches; abort
            return
        # Delete existing plugin
        manage_delAuth0(zport_acl, PLUGIN_ID)

    manage_addAuth0(zport_acl, PLUGIN_ID, PLUGIN_TITLE)

    interfaces = ('IAuthenticationPlugin', 'IExtractionPlugin', 'IChallengePlugin')
    activatePluginForInterfaces(zport_acl, PLUGIN_ID, interfaces)

    movePluginToTop(zport_acl, PLUGIN_ID, 'IAuthenticationPlugin')
    movePluginToTop(zport_acl, PLUGIN_ID, 'IChallengePlugin')
