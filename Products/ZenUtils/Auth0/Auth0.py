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
                                                              IChallengePlugin,
                                                              ICredentialsResetPlugin,
                                                              IRolesPlugin)
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.ZenUtils.AuthUtils import getJWKS, publicKeysFromJWKS
from Products.ZenUtils.CSEUtils import getZenossURI
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.PASUtils import activatePluginForInterfaces, movePluginToTop

import base64
import httplib
import json
import jwt
import logging
import time

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'
PLUGIN_VERSION=3

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
    log.info('Added Auth0 PAS Plugin')

def manage_delAuth0(context, id):
    context._delObject(id)
    log.info('Deleted Auth0 PAS Plugin')


class SessionInfo(object):
    def __init__(self):
        for i in ['userid', 'expiration', 'refreshToken', 'roles']:
            setattr(self, i, '')

class Auth0(BasePlugin):
    """Auth0 is a PluggableAuthService MultiPlugin which satisfies interfaces:
        IExtractionPlugin
        IAuthenticationPlugin
        IChallengePlugin
        ICredentialsResetPlugin

    It aims to provide authentication via Auth0, and supports reading tokens
        from a cookie, the Authorization header, or query args
    """

    meta_type = 'Auth0 plugin'
    session_key = 'auth0'
    cache = {}

    def __init__(self, id, title=None):
        self._id = self.id = id
        self.title = title
        self.version = PLUGIN_VERSION


    @staticmethod
    def _getKey(key_id, conf):
        """ Look up a key in the cached list of keys.
            If we have never looked up a given key, refresh the cache.
         """
        if 'keys' not in Auth0.cache or key_id not in Auth0.cache['keys']:
            jwks = getJWKS(conf['tenant'] + '.well-known/jwks.json')
            Auth0.cache['keys'] = publicKeysFromJWKS(jwks)
        return Auth0.cache['keys'].setdefault(key_id, None)

    @staticmethod
    def storeIdToken(id_token, session, conf, refresh_token):
        """ Save the important parts of the token in session storage.
            Returns the corresponding SessionInfo object.
        """
        # get the key id from the jwt header
        key_id = jwt.get_unverified_header(id_token)['kid']
        key = Auth0._getKey(key_id, conf)
        if not key:
            session.pop(Auth0.session_key, None)
            log.warn('Invalid jwt kid (key id) - not setting session info')
            return None

        payload = jwt.decode(id_token, key, verify=True,
                             algorithms=['RS256'],
                             audience=conf['clientid'],
                             issuer=conf['tenant'])

        sessionInfo = SessionInfo()
        sessionInfo.userid = payload['sub'].encode('utf8').split('|')[-1]
        sessionInfo.expiration = payload['exp']
        sessionInfo.roles = payload['https://zenoss.com/roles']
        sessionInfo.refreshToken = refresh_token
        session.set(Auth0.session_key, sessionInfo)
        return sessionInfo


    @staticmethod
    def _refreshToken(session, conf):
        """ Refresh an expired token
            Returns the SessionInfo object from the new token
        """
        refresh_token = session.get(Auth0.session_key, SessionInfo()).refreshToken
        if not refresh_token:
            log.warn('No refresh token - not getting new id token')
            return None

        data = {
            "grant_type": "refresh_token",
            "client_id": conf['clientid'],
            "client_secret": conf['client-secret'],
            "refresh_token": refresh_token
        }

        domain = conf['tenant'].replace('https://', '').replace('/', '')
        conn = httplib.HTTPSConnection(domain)
        headers = {"content-type": "application/json"}
        try:
            conn.request('POST', '/oauth/token', json.dumps(data), headers)
            resp_string = conn.getresponse().read()
        except Exception as a:
            log.error('Unable to obtain new token from Auth0: %s', a)
            return None

        resp_data = json.loads(resp_string)
        id_token = resp_data.get('id_token')
        log.debug('Token refreshed')

        return Auth0.storeIdToken(id_token, session, conf, refresh_token)


    def resetCredentials(self, request, response):
        """resetCredentials satisfies the PluggableAuthService
            ICredentialsResetPlugin interface.
        The Auth0 session variables are cleared and the user is redirected to
            the Auth0 logout in order to end their Auth0 SSO session.
        NOTE:
        Logging out of the UI calls Products/ZenModel/skins/zenmodel/logoutUser.py
            which calls resetCredentials, this bypasses the PAS logout.
        """
        if Auth0.session_key in request.SESSION:
            del request.SESSION[Auth0.session_key]
        conf = getAuth0Conf()
        if conf:
            response.redirect('%sv2/logout?' % conf['tenant'] +
                              'client_id=%s&' % conf['clientid'] +
                              'returnTo=%s/zport/dmd' % getZenossURI(request),
                              lock=True)
            log.info('Redirecting user to Auth0 logout')


    def extractCredentials(self, request):
        """extractCredentials satisfies the PluggableAuthService
            IExtractionPlugin interface.
        A successful extraction will return a dict with the 'auth0_userid' field
            containing the userid.
        """
        conf = getAuth0Conf()
        if not conf:
            log.debug('Incomplete Auth0 config in GlobalConfig - not using Auth0 login')
            return {}

        sessionInfo = request.SESSION.get(Auth0.session_key)
        if not sessionInfo:
            log.debug('No Auth0 session - not directing to Auth0 login')
            return {}

        if time.time() > sessionInfo.expiration:
            log.debug('Token expired - attempting to refresh')
            sessionInfo = Auth0._refreshToken(request.SESSION, conf)

        if not sessionInfo or not sessionInfo.userid:
            log.debug('No Auth0 session - not directing to Auth0 login')
            return {}

        return {'auth0_userid': sessionInfo.userid}


    def authenticateCredentials(self, credentials):
        """authenticateCredentials satisfies the PluggableAuthService
            IAuthenticationPlugin interface.
        A successful authentication will return (userid, userid).
        """
        # Ignore credentials that are not from our extractor
        if credentials.get('extractor') != PLUGIN_ID:
            return None

        userid = credentials.get('auth0_userid')
        if not userid:
            log.debug('No userid in credentials')
            return None

        return (userid, userid)


    def challenge(self, request, response):
        """challenge satisfies the PluggableAuthService
            IChallengePlugin interface.
        """
        conf = getAuth0Conf()
        if not conf or not all(conf.values()):
            log.debug('Incomplete Auth0 config in GlobalConfig - not directing to Auth0 login')
            return False

        zenoss_uri = getZenossURI(request)
        # pass state to auth0 so we can redirect user to where they wanted to go
        state_obj = {
            "came_from": request.ACTUAL_URL
        }
        state = base64.urlsafe_b64encode(json.dumps(state_obj))

        uri = "%sauthorize?" % conf['tenant'] + \
              "response_type=code&" + \
              "client_id=%s&" % conf['clientid'] + \
              "state=%s&" % state + \
              "scope=openid offline_access&" + \
              "prompt=none&" + \
              "redirect_uri=%s/zport/Auth0Callback" % zenoss_uri

        request['RESPONSE'].redirect(uri, lock=1)
        return True

    def getRolesForPrincipal(self, principal, request=None):
        """ Implements PluggableAuthService IRolesPlugin interface.
            principal -> ( role_1, ... role_N )
            o Return a sequence of role names which the principal has.
            o May assign roles based on values in the REQUEST object, if present.
        """
        if not request:
            return ()
        sessionInfo = request.SESSION.get(Auth0.session_key)
        if not sessionInfo:
            log.debug('No Auth0 session - not getting roles for user')
            return ()
        if not sessionInfo.roles:
            log.debug('No roles in Auth0 session - not returning roles')
            return ()
        return set(sessionInfo.roles)

classImplements(Auth0,
                IAuthenticationPlugin,
                IExtractionPlugin,
                IChallengePlugin,
                ICredentialsResetPlugin,
                IRolesPlugin)

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

    interfaces = ('IAuthenticationPlugin',
                  'IExtractionPlugin',
                  'IChallengePlugin',
                  'ICredentialsResetPlugin',
                  'IRolesPlugin')
    activatePluginForInterfaces(zport_acl, PLUGIN_ID, interfaces)

    movePluginToTop(zport_acl, PLUGIN_ID, 'IAuthenticationPlugin')
    movePluginToTop(zport_acl, PLUGIN_ID, 'IChallengePlugin')
