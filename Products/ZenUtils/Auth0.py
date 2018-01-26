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

import json
import urllib
import jwt
import logging

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'

AUTH0_CLIENT_ID = 'cTxVLXKTNloQv1GN9CSRAds5C4PpTkac'
AUTH0_ISSUER = 'https://zenoss-dev.auth0.com/'
AUTH0_JWKS_LOCATION = 'https://zenoss-dev.auth0.com/.well-known/jwks.json'

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

def manage_addAuth0(context, id, title=None, REQUEST=None):

    obj = Auth0(id, title)
    context._setObject(obj.getId(), obj)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


class Auth0(BasePlugin):

    """
    """

    meta_type = 'Auth0 plugin'

    def __init__(self, id, title=None):
        self._id = self.id = id
        self.title = title

    def extractCredentials(self, request):
        def getTokenFromHeader():
            auth = request._auth
            if auth is None or len(auth) < 9 or auth[:7].lower() != 'bearer ':
                return None
            return auth.split()[-1]

        def getTokenFromQuery():
            for arg in request.QUERY_STRING.split('&'):
                parts = arg.split('=')
                if len(parts) == 2 and parts[0] == 'idToken':
                    return parts[1]
            return None

        auth = getTokenFromHeader() or getTokenFromQuery()
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

        # get the key id from the jwt header
        kid = jwt.get_unverified_header(credentials['token'])['kid']

        # get the public keys from the jwks
        jwks = getJWKS(AUTH0_JWKS_LOCATION)
        keys = publicKeysFromJWKS(jwks)

        # if the kid from the jwt isn't in our keys, bail
        key = keys.get(kid)
        if key == None:
            return None

        payload = jwt.decode(credentials['token'], key, verify=True,
                             algorithms=['RS256'], audience=AUTH0_CLIENT_ID,
                             issuer=AUTH0_ISSUER)
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
        try:
            req = self.REQUEST
            resp = req['RESPONSE']

            resp.redirect("https://zenoss-dev.auth0.com/authorize?"+
                          "response_type=token id_token&"+
                          "client_id=%s&" % AUTH0_CLIENT_ID +
                          "connection=example&"+
                          "nonce=abcd1234&"+
                          "redirect_uri=https://zenoss5.zenoss-1423-ld/zport/callback",
                          lock=1)
            return True
        except:
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

    if hasattr(zport_acl, PLUGIN_ID):
        return

    manage_addAuth0(zport_acl, PLUGIN_ID, PLUGIN_TITLE)

    interfaces = ('IAuthenticationPlugin', 'IExtractionPlugin', 'IChallengePlugin')
    activatePluginForInterfaces(zport_acl, PLUGIN_ID, interfaces)

    movePluginToTop(zport_acl, PLUGIN_ID, 'IAuthenticationPlugin')
    movePluginToTop(zport_acl, PLUGIN_ID, 'IChallengePlugin')
