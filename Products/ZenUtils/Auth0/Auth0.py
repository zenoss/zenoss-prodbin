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
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.PASUtils import activatePluginForInterfaces, movePluginToTop
from zope.component import getUtility
from Products.ZenUtils.virtual_root import IVirtualRoot

import base64
import jwt
import logging
import time

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'
PLUGIN_VERSION = 3

_AUTH0_CONFIG = {
    'audience': None,
    'tenant': None,
    'whitelist': None,
    'tenantkey': None,
    'emailkey': None,
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
        if not all(d.values()) and any(d.values()):
            raise Exception('Auth0 config is missing values. Expecting: %s' % ', '.join(['auth0-%s' % value for value in _AUTH0_CONFIG.keys()]))
        _AUTH0_CONFIG = d if all(d.values()) else None
        # Whitelist is a comma separated array of strings
        if _AUTH0_CONFIG and _AUTH0_CONFIG['whitelist']:
            _AUTH0_CONFIG['whitelist'] = [s.strip() for s in _AUTH0_CONFIG['whitelist'].split(',') if s.strip() != '']
    return _AUTH0_CONFIG or None

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

    zc_token_key = 'accessToken'

    meta_type = 'Auth0 plugin'
    session_key = 'auth0'
    cookie_key = 'zauth0_key'
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
    def removeToken(request):
        request.SESSION.pop(Auth0.session_key, None)
        if request.response:
            request.response.expireCookie(Auth0.zc_token_key)

    @staticmethod
    def storeToken(token, request, conf):
        """ Save the important parts of the token in session storage.
            Returns the corresponding SessionInfo object.  If we can't
            return the object for any reason, we remove the Auth0 information
            from the session and expire the cookie.
        """
        try:
            session = request.SESSION
            # get the key id from the jwt header
            key_id = jwt.get_unverified_header(token)['kid']
            key = Auth0._getKey(key_id, conf)
            if not key:
                log.warn('Invalid jwt kid (key id) - not setting session info')
                Auth0.removeToken(request)
                return None

            payload = jwt.decode(token, key, verify=True,
                                 algorithms=['RS256'],
                                 audience=conf['audience'],
                                 issuer=conf['tenant'])

            # Make sure we have an auth0 conf
            conf = conf or getAuth0Conf()
            if not conf:
                log.warn('Incomplete Auth0 config in GlobalConfig - not using Auth0 login')
                Auth0.removeToken(request)
                return None

            # Verify that the tenant is in our whitelist.
            # + The tenantkey is used to lookup the tenant from the jwt.
            tenantkey = conf.get('tenantkey', 'https://dev.zing.ninja/tenant')
            tenant = payload.get(tenantkey, None) # ie: "https://dev.zing.ninja/tenant": "alphacorp", in jwt
            if not tenant:
                log.warn('No auth0 tenant specified in jwt for tenantkey: {}'.format(tenantkey))
                Auth0.removeToken(request)
                return None
            # + Get the whitelist from global.conf and verify that it's in the list.
            whitelist = conf.get('whitelist', [])
            if not tenant in whitelist:
                log.warn('Tenant {} is invalid. Not in whitelist: {}'.format(tenant, whitelist))
                Auth0.removeToken(request)
                return None

            emailkey = conf.get('emailkey', 'https://dev.zing.ninja/email')
            email = payload.get(emailkey, None)

            sessionInfo = session.setdefault(Auth0.session_key, SessionInfo())
            # use the email as the userid, if defined, otherwise fall back to parsing the sub field.
            if email:
                sessionInfo.userid = email
            else:
                sessionInfo.userid = payload['sub'].encode('utf8').split('|')[-1]
            sessionInfo.expiration = payload['exp']
            sessionInfo.roles = payload.get('https://zenoss.com/roles', [])
            return sessionInfo
        except Exception as ex:
            log.debug('Error storing jwt token: {}'.format(ex.message))
            Auth0.removeToken(request)
            return None

    def resetCredentials(self, request, response):
        """resetCredentials satisfies the PluggableAuthService
            ICredentialsResetPlugin interface.
        Clears the session, removes the Auth0 cookie, then redirects to the
            ZING logout url.  Removal of the cookie effectively logs the user
            out of all CZ instances, and the redirect will log the user out
            of ZING.
        NOTE:
        Logging out of the UI calls Products/ZenModel/skins/zenmodel/logoutUser.py
            which calls resetCredentials, this bypasses the PAS logout.
        """
        # Clear session variables and redirect to the ZC logout.
        request.SESSION.clear()
        response.expireCookie(Auth0.zc_token_key)
        conf = getAuth0Conf()
        if conf:
            log.info('Redirecting user to Auth0 logout: %s' % conf)
            response.redirect("/logout.html")


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

        token = request.cookies.get(Auth0.zc_token_key, None)
        if not token:
            log.debug('No Auth0 token found in cookies')
            return {}

        sessionInfo = request.SESSION.get(Auth0.session_key)
        if not sessionInfo:
            sessionInfo = Auth0.storeToken(token, request, conf)

        if not sessionInfo or not sessionInfo.userid:
            log.debug('No userid found in sessionInfo - not directing to Auth0 login')
            Auth0.removeToken(request)
            return {}

        if time.time() > sessionInfo.expiration:
            # The stored session data is invalid, and we're using Auth0; remove the Auth0 data
            # from the session.
            Auth0.removeToken(request)
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

        # It's possible for a fresh start to get here, but ZC has already logged us in.  If we have
        # a jwt token, try to use that before redirecting to ZC.
        sessionInfo = request.SESSION.get(Auth0.session_key)
        if not sessionInfo:
            token = request.cookies.get(Auth0.zc_token_key, None)
            if token:
                sessionInfo = self.storeToken(token, request, conf)
                if sessionInfo:
                    return True

        currentLocation = getUtility(IVirtualRoot).ensure_virtual_root(request.PATH_INFO)
        redirect = base64.urlsafe_b64encode(currentLocation)
        request['RESPONSE'].redirect('/czlogin.html?redirect={}'.format(redirect), lock=1)
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
