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
import json
import jwt
import logging
import os
import urllib
from datetime import datetime, timedelta

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'
PLUGIN_VERSION=1

_AUTH0_CONFIG = {
        'clientid': None,
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
    cookie_name = '__macaroon'
    nonce_cookie = '__auth_nonce'
    state_cookie = '__auth_state'
    cache = {}

    def __init__(self, id, title=None):
        self._id = self.id = id
        self.title = title
        self.version = PLUGIN_VERSION
        # TODO: use memcache

    def extractCredentials(self, request):
        """extractCredentials satisfies the PluggableAuthService
            IExtractionPlugin interface.
        A successful extraction will return a dict with the 'token' field
            containing a jwt.
        """
        auth = request.get(self.cookie_name) or getBearerToken(request)
        if not auth:
            query_args = getQueryArgsFromRequest(request)
            auth = query_args.get('idToken') or query_args.get('accessToken')
        return {'token': auth} if auth else {}

    def authenticateCredentials(self, credentials):
        """authenticateCredentials satisfies the PluggableAuthService
            IAuthenticationPlugin interface.
        A successful authentication will return (userid, userid).
        """
        # Ignore credentials that are not from our extractor
        if credentials.get('extractor') != PLUGIN_ID or \
           'token' not in credentials:
            return None

        conf = getAuth0Conf()
        if not conf:
            return None

        token = credentials['token']

        # get the key id from the jwt header
        kid = jwt.get_unverified_header(token)['kid']

        # get the public keys from the jwks
        keys = self.cache.get('keys')
        # if we don't have the keys in cache or
        #  if the kid from the jwt isn't in our keys, update cache
        if not keys or kid not in keys:
            jwks = getJWKS(conf['tenant'] + '.well-known/jwks.json')
            keys = publicKeysFromJWKS(jwks)
            self.cache['keys'] = keys

        # if we still don't have that kid, it's not a token we can use
        key = keys.get(kid)
        if not key:
            return None

        # TODO: handle expired token
        payload = jwt.decode(token, key, verify=True,
                             algorithms=['RS256'], audience=conf['clientid'],
                             issuer=conf['tenant'])
        if not payload or 'sub' not in payload:
            return None

        # Auth0 "sub" format is: connection|user or method|connection|user
        userid = payload['sub'].encode('utf8').split('|')[-1]
        return (userid, userid)

    def challenge(self, request, response):
        """challenge satisfies the PluggableAuthService
            IChallengePlugin interface.
        """
        conf = getAuth0Conf()
        if not conf or not all(conf):
            return False

        zenoss_uri = getZenossURI(request)
        nonce = base64.urlsafe_b64encode(os.urandom(32))
        # pass state to auth0 so we can redirect user to where they wanted to go
        state_obj = {
            "came_from": request.ACTUAL_URL
        }
        state = base64.urlsafe_b64encode(json.dumps(state_obj))
        # set expiration on cookies, otherwise they will expire with the session
        # user has 30 minutes to authenticate with Auth0
        expiration_time = datetime.utcnow() + timedelta(minutes=30)
        expiration = expiration_time.strftime("%a, %d %b %Y %X %Z")
        response.setCookie(self.nonce_cookie, nonce, expires=expiration,
                           path="/", secure=True, http_only=True)
        response.setCookie(self.state_cookie, state, expires=expiration,
                           path="/", secure=True, http_only=True)

        request['RESPONSE'].redirect("%sauthorize?" % conf['tenant'] +
                                     "response_type=token id_token&" +
                                     "client_id=%s&" % conf['clientid'] +
                                     "connection=%s&" % conf['connection'] +
                                     "nonce=%s&" % nonce +
                                     "state=%s&" % state +
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
