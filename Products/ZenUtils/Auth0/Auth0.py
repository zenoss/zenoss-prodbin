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
                                                              IRolesPlugin,
                                                              IPropertiesPlugin)
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.ZenMessaging.audit import audit
from Products.ZenUtils.AuthUtils import getJWKS, publicKeysFromJWKS
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.PASUtils import activatePluginForInterfaces, movePluginToTop
from zope.component import getUtility
from Products.ZenUtils.virtual_root import IVirtualRoot
import memcache

import base64
import jwt
import logging
import re
import time

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'
PLUGIN_VERSION = 4
MEMCACHED_IMPORT = ('localhost', '11211')

rbac_pattern = re.compile("^(internal:)?(CZ[0-9]+):(.+)")
email_pattern = re.compile("^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

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

def get_ip(request):
    if "HTTP_X_FORWARDED_FOR" in request.environ:
        # Virtual host
        # This can be a comma-delimited list of IPs but we are fine with
        # logging multiple IPs for auditing at this time.
        ip = request.environ["HTTP_X_FORWARDED_FOR"]
    elif "HTTP_HOST" in request.environ:
        # Non-virtualhost
        ip = request.environ["REMOTE_ADDR"]
    else:
        ip = getattr(request, '_client_addr', 'Unknown')

    return ip

def manage_addAuth0(context, id, title=None):
    obj = Auth0(id, title)
    context._setObject(obj.getId(), obj)
    log.info('Added Auth0 PAS Plugin')

def manage_delAuth0(context, id):
    context._delObject(id)
    log.info('Deleted Auth0 PAS Plugin')


class SessionInfo(object):
    ATTRIBUTES = ['userid', 'expiration', 'refreshToken', 'roles']

    def __init__(self):
        for i in SessionInfo.ATTRIBUTES:
            setattr(self, i, '')

    def __str__(self):
        output = ''
        for i in SessionInfo.ATTRIBUTES:
            output += '{}:{}, '.format(i, getattr(self, i))
        return output.strip(', ')


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
    zc_token_exp_key = 'accessTokenExpiration'

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
    def getRoleAssignments(roles=None):
        """
        This looks for RBAC style roles in the role list ("CZ0:CZAdmin"), and uses those if they exist.  If they
        don't exist, return the roles as-is (they may contain older style roles, ie, "CZAdmin" for Zenoss-com
        connections).

        :param roles:an array of roles, possibly in RBAC format (strings), [ "CZ0:ZenManager", "CZ0:ZenUser", .. ]
        :return: an array of roles (strings), [ "ZenManager", "ZenUser", .. ]
        """
        if not roles:
            return []

        # The cz_prefix for this CZ is going to be "CZ#", ie: "CZ0", "CZ1", ..
        cz_prefix = getUtility(IVirtualRoot).get_prefix().strip("/").upper()

        # RBAC style roles are in the form: "CZ#:ZenManager". If our user has any RBAC style role mappings, we need to
        # return only RBAC assigned roles.  This covers the case where we were assigned CZ1:ZenManager and not assigned
        # any roles for CZ0.  We shouldn't return the older gsuite group mappings for this user in this case.
        matches = [rbac_pattern.match(role) for role in roles]

        # filter non-matches (None) without evaluating the regex a second time.
        matches = [match for match in matches if match]

        # If there are any RBAC roles assigned, use only the RBAC roles for this CZ.
        if matches:
            # for an RBAC role: "CZ0:ZenManager", match.group(3) = "ZenManager", match.group(2) = "CZ0"
            # if this has the optional beginning "internal:CZ0:ZenManager", match(1) is "internal:" and unused.
            return [match.group(3) for match in matches if match.group(2) == cz_prefix]

        return []

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
            # Check the jwt for the globalkey setting.
            is_global_key = payload.get('https://dev.zing.ninja/globalkey', None)
            if not is_global_key and not tenant:
                log.warn('No auth0 tenant specified in jwt for tenantkey: {}'.format(tenantkey))
                Auth0.removeToken(request)
                return None
            # + Get the whitelist from global.conf and verify that it's in the list.
            whitelist = conf.get('whitelist', [])
            if not is_global_key and tenant not in whitelist:
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
            sessionInfo.roles = Auth0.getRoleAssignments(payload.get('https://zenoss.com/roles', []))
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
        response.expireCookie(Auth0.zc_token_exp_key)
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
            ipaddress = get_ip(request)
            audit('UI.Authentication.Valid', username_=sessionInfo.userid, ipaddress=ipaddress)

        # ZING-821: We need to verify that the session data we've cached matches the
        # token expiration.  If the expiration cookie is set, make sure it matches
        # our cache - otherwise we need to parse the access token again.
        token_expiration = request.cookies.get(Auth0.zc_token_exp_key, None)
        if sessionInfo and token_expiration:
            # ZING stores the expiration *1000 instead of the expiration value (why??), so we
            # have to adjust to compare to our cached session expiration from the token.
            token_expiration = int(token_expiration) / 1000
            if not sessionInfo.expiration == token_expiration:
                log.info('Token expiration does not match stored expiration. Parsing token again.')
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
        
        log.info('sessionInfo.roles: {}'.format(sessionInfo.roles))
        if len(sessionInfo.roles) < 1:
            log.info('No roles for this CZ - redirecting ...')
            return {'has_roles': False}

        return {'auth0_userid': sessionInfo.userid}


    def authenticateCredentials(self, credentials):
        """authenticateCredentials satisfies the PluggableAuthService
            IAuthenticationPlugin interface.
        A successful authentication will return (userid, userid).
        """
        # Ignore credentials that are not from our extractor
        if credentials.get('extractor') != PLUGIN_ID:
            return None

        if credentials.get('has_roles') is False:
            log.debug('authenticateCredentials: has_roles: False')
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

        # ZING-805: Unauthorized access to a page results in an infinite loop as Zope issues a challenge (which
        # redirects to ZING), then ZING says you're already logged in and sends you back. This uses memcache (so
        # each zope gets the same data) to store the token expiration for each user, to detect a redirect loop
        # between RM<->ZING. If a redirect loop is detected, the user is sent to the ZING home page.  Note that
        # sessionInfo doesn't persist the auth_expiration property when modified outside of the initial storage,
        # and a local dictionary isn't available to all zopes.
        if sessionInfo:
            mc = memcache.Client(MEMCACHED_IMPORT, debug=0)
            EXPIRATION_KEY = 'auth0_{}_expiration_key'.format(sessionInfo.userid)
            auth_exp = mc.get(EXPIRATION_KEY)
            if auth_exp == sessionInfo.expiration:
                log.warn('Unauthorized access (user {}): {}'.format(sessionInfo.userid, request.PATH_INFO))
                # This is a redirect loop. send them to the Zing UI
                mc.delete(EXPIRATION_KEY)
                request['RESPONSE'].redirect('/', lock=1)
                return True
            # store the token expiration and send them to the login.  If zing sends them back without
            # logging them in again (the same expiration), then that's a redirect loop.
            mc.set(EXPIRATION_KEY, sessionInfo.expiration)
            
            # ZING-1627: If a user has no CZ roles on this instance, then redirect them to the Zenoss Cloud UI with
            # `errcode=1`, which means "Missing required permissions"
            # See https://github.com/zenoss/zing-web/blob/feature/delegateToCZModal/packages/z-common/src/mixins/ZErrorCodes.js#L6
            # Concurrent, with this change, the ZC UI is being updated to use a modal component
            # that is activated when the query parameter, `errcode` is passed.
            if len(sessionInfo.roles) < 1:
                mc.delete(EXPIRATION_KEY)
                request['RESPONSE'].redirect('/#/?errcode=1', lock=1)
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
        # to avoid the issue in ZEN-31732 - CZ-only users can still see all the events
        return set(sessionInfo.roles) - set(["Delegate to Collection Zone"])

    def getPropertiesForUser(self, user, request=None):
        """ ImplementesPluggableAuthService  IPropertiesPlugin interface.
            o Return properties for auth0 user
        """
        if not request:
            return {}
        sessionInfo = request.SESSION.get(Auth0.session_key)
        if getattr(sessionInfo, 'userid'):
            # userid is not always an email; see method storeToken
            if email_pattern.match(sessionInfo.userid):
                return {'email': sessionInfo.userid}
        return {}

classImplements(Auth0,
                IAuthenticationPlugin,
                IExtractionPlugin,
                IChallengePlugin,
                ICredentialsResetPlugin,
                IRolesPlugin,
                IPropertiesPlugin)

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
                  'IRolesPlugin',
                  'IPropertiesPlugin')
    activatePluginForInterfaces(zport_acl, PLUGIN_ID, interfaces)

    movePluginToTop(zport_acl, PLUGIN_ID, 'IAuthenticationPlugin')
    movePluginToTop(zport_acl, PLUGIN_ID, 'IChallengePlugin')
