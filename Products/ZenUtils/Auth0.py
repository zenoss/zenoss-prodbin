##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from AccessControl import AuthEncoding
from AccessControl import ClassSecurityInfo
from AccessControl.class_init import InitializeClass

from BTrees.OOBTree import OOBTree
from DateTime import DateTime
from OFS.Folder import Folder
from exceptions import Exception

from Products.CMFCore.utils import getToolByName
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Products.PluggableAuthService.interfaces.plugins import (IExtractionPlugin,
                                                            IAuthenticationPlugin)

from Products.PluggableAuthService.permissions import ManageUsers
from Products.PluggableAuthService.plugins.BasePlugin import BasePlugin
from Products.PluggableAuthService.utils import classImplements

import jwt
import logging

log = logging.getLogger('Auth0')

TOOL = 'Auth0'
PLUGIN_ID = 'auth0_plugin'
PLUGIN_TITLE = 'Provide auth via Auth0 service'

class Locked(Exception):
    pass


def manage_addAuth0(context, id, title=None, REQUEST=None):

    obj = Auth0(id, title)
    context._setObject(obj.getId(), obj)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path()+'/manage_main')


class Auth0(BasePlugin):

    """
    """

    meta_type = 'Auth0 plugin'
    security = ClassSecurityInfo()

    def __init__(self, id, title=None):
        self._id = self.id = id
        self.title = title


    def authenticateCredentials(self, credentials):
        """
        """
        # Ignore credentials that are not from our extractor
        extractor = credentials.get('extractor')
        if extractor != PLUGIN_ID:
            return None

        payload = self._decode_token(credentials['token'])
        if not payload:
            return None

        if 'sub' not in payload:
            return None

        userid = payload['sub'].encode('utf8')

        return (userid, userid)

    def _decode_token(self, token, verify=True):
	return self._jwt_decode(
	    token, 'secret', verify=verify)

    def _jwt_decode(self, token, secret, verify=True):
        try:
            return jwt.decode(
                token, secret, verify=verify, algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return None

    def extractCredentials(self, request):
        creds = {}
        auth = request._auth
        if auth is None:
            return None
        if auth[:7].lower() == 'bearer ':
            creds['token'] = auth.split()[-1]
        else:
            return None

        return creds


    def getRootPlugin(self):
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


classImplements(Auth0, IAuthenticationPlugin, IExtractionPlugin)

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
    
    app_acl = getToolByName(app, 'acl_users')
    zport_acl = getToolByName(zport, 'acl_users')

    if hasattr(app_acl, PLUGIN_ID):
        return

    context_interfaces = {app_acl:('IAuthenticationPlugin', 'IExtractionPlugin'),
                zport_acl:('IAuthenticationPlugin', 'IExtractionPlugin')}

    for context in context_interfaces:
        manage_addAuth0(context, PLUGIN_ID, PLUGIN_TITLE)

    for context, interfaces in context_interfaces.iteritems():
        activatePluginForInterfaces(context, PLUGIN_ID, interfaces)

    for context in context_interfaces:
        movePluginToTop(context, PLUGIN_ID, 'IAuthenticationPlugin')

