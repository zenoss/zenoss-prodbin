##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from AccessControl.class_init import InitializeClass

from OFS.Folder import Folder

from Products.CMFCore.utils import getToolByName

from Products.PluggableAuthService.interfaces.plugins import (IExtractionPlugin,
                                                            IAuthenticationPlugin,
                                                            IChallengePlugin)

from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

import base64
import json
import urllib
import jwt
import logging
from datetime import datetime, timedelta

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'

AUTH0_CONFIG = {}
CSE_CONFIG = {}
PLUGIN_VERSION=1

def getAuth0Conf():
    if not (AUTH0_CONFIG.get('clientid') and AUTH0_CONFIG.get('tenant') and AUTH0_CONFIG.get('connection')):
        config = getGlobalConfiguration()
        AUTH0_CONFIG['clientid'] = config.get('auth0-clientid', 'cTxVLXKTNloQv1GN9CSRAds5C4PpTkac')
        AUTH0_CONFIG['tenant'] = config.get('auth0-tenant', 'https://zenoss-dev.auth0.com/')
        AUTH0_CONFIG['connection'] = config.get('auth0-connection', 'acme')
    return AUTH0_CONFIG

def getCSEConf():
    if not (CSE_CONFIG.get('vhost') and CSE_CONFIG.get('virtualroot') and CSE_CONFIG.get('zing-host')):
        config = getGlobalConfiguration()
        CSE_CONFIG['vhost'] = config.get('cse-vhost')
        CSE_CONFIG['virtualroot'] = config.get('cse-virtualroot')
        CSE_CONFIG['zing-host'] = config.get('cse-zing-host')
    return CSE_CONFIG

def getZenossURI(request):
    # if we aren't running as a cse, get uri from request
    cse_conf = getCSEConf()
    zenoss_uri = "https://"
    if cse_conf['vhost'] and cse_conf['zing-host'] and cse_conf['virtualroot']:
        zenoss_uri += cse_conf['vhost'] + '.' + cse_conf['zing-host'] + '/' + cse_conf['virtualroot']
    else:
        # HTTP_X_FORWARDED_HOST should handle vhost
        zenoss_uri += request.environ.get("HTTP_X_FORWARDED_HOST") or \
                      request.environ.get("HTTP_HOST")
    return zenoss_uri

def getJWKS(jwks_url):
    try:
        # we should cache this and use the cached one until a token comes in
        #   with a kid other than what's in our cached jwks
        resp = urllib.urlopen(jwks_url)
        return json.load(resp)
    except Exception as e:
        print e
        # we probably want to handle an error here somehow
        return None

def publicKeysFromJWKS(jwks):
    public_keys = {}
    for key in jwks['keys']:
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        public_keys[key['kid']] = public_key
    return public_keys

def getQueryArgs(request):
    query_args = {}
    for arg in request.QUERY_STRING.split('&'):
        parts = arg.split('=')
        if len(parts) == 2:
            query_args[parts[0]] = parts[1]
    return query_args

def manage_addAuth0(context, id, title=None):
    obj = Auth0(id, title)
    context._setObject(obj.getId(), obj)

def manage_delAuth0(context, id):
    context._delObject(id)

class Auth0(BasePlugin):

    """
    """

    meta_type = 'Auth0 plugin'
    cache = {}

    def __init__(self, id, title=None):
        self._id = self.id = id
        self.title = title
        self.version = PLUGIN_VERSION

    def extractCredentials(self, request):
        def getTokenFromHeader():
            auth = request._auth
            if auth is None or len(auth) < 9 or auth[:7].lower() != 'bearer ':
                return None
            return auth.split()[-1]

        auth = request.get('__macaroon') or getTokenFromHeader() or getQueryArgs(request).get('idToken', None)
        if auth is None:
            return {}
        return {'token': auth}

    def authenticateCredentials(self, credentials):
        """
        """
        # Ignore credentials that are not from our extractor
        extractor = credentials.get('extractor')
        if extractor != PLUGIN_ID:
            return None

        conf = getAuth0Conf()

        # get the key id from the jwt header
        kid = jwt.get_unverified_header(credentials['token'])['kid']

        # get the public keys from the jwks
        keys = self.cache.get('keys', None)
        if keys is None:
            jwks = getJWKS(conf['tenant'] + '.well-known/jwks.json')
            keys = publicKeysFromJWKS(jwks)
            self.cache['keys'] = keys

        # if the kid from the jwt isn't in our keys, bail
        key = keys.get(kid, None)
        if key is None:
            return None

        payload = jwt.decode(credentials['token'], key, verify=True,
                             algorithms=['RS256'], audience=conf['clientid'],
                             issuer=conf['tenant'])
        if not payload:
            return None

        if 'sub' not in payload:
            return None

        # Auth0 "sub" format is: connection|user
        userid = payload['sub'].encode('utf8').split('|')[-1]

        print "Auth0: authenticateCredentials userid:", userid
        return (userid, userid)

    def challenge(self, request, response):
        """Redirect to Auth0
        """
        conf = getAuth0Conf()
        zenoss_uri = getZenossURI(request)
        state_obj = {
                "came_from": request.ACTUAL_URL
            }
        # strip the '=' padding because js doesn't need it
        state = base64.urlsafe_b64encode(json.dumps(state_obj))#.replace("=", '')
        nonce = "abcd1234"
        # set expiration on our cookies, since they will otherwise expire with the session
        expiration_time = datetime.utcnow() + timedelta(minutes=5)
        expiration = expiration_time.strftime("%a, %d %b %Y %X %Z")
        response.setCookie('__auth_nonce', nonce, expires=expiration, path="/")
        response.setCookie('__auth_state', state, expires=expiration, path="/")
        try:
            request['RESPONSE'].redirect("%sauthorize?" % conf['tenant'] +
                                         "response_type=token id_token&" +
                                         "client_id=%s&" % conf['clientid'] +
                                         "connection=%s&" % conf['connection'] +
                                         "nonce=%s&" % nonce +
                                         "state=%s&" % state +
                                         "redirect_uri=%s/zport/callback" % zenoss_uri,
                                         lock=1)
            return True
        except Exception as e:
            print "EXCEPTION:", e
            return False

    def getRootPlugin(self):
        # do we need this?
        pas = self.getPhysicalRoot().acl_users
        plugins = pas.objectValues([self.meta_type])
        if plugins:
            return plugins[0]

    #
    #   ZMI
    #
    manage_options = (
        (
            {'label': 'Users',
                'action': 'manage_users', },
        )
        + BasePlugin.manage_options[:1]
        + Folder.manage_options[:1]
        + Folder.manage_options[2:]
    )


classImplements(Auth0, IAuthenticationPlugin, IExtractionPlugin, IChallengePlugin)

InitializeClass(Auth0)

def setup(context):

    def activatePluginForInterfaces(pas, plugin, selected_interfaces):
        plugin_obj = pas[plugin]
        activatable = []
        for info in plugin_obj.plugins.listPluginTypeInfo():
            interface = info['interface']
            interface_name = info['id']
            if plugin_obj.testImplements(interface) and \
                    interface_name in selected_interfaces:
                    activatable.append(interface_name)

        plugin_obj.manage_activateInterfaces(activatable)


    def movePluginToTop(pas, plugin_id, interface_name):
        plugin_registry = pas.plugins
        interface = plugin_registry._getInterfaceFromName(interface_name)
        while plugin_registry.listPlugins(interface)[0][0] != plugin_id:
            plugin_registry.movePluginsUp(interface, [plugin_id])


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
