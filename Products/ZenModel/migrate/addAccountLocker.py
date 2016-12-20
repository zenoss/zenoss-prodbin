##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__='''
This migration script adds AccountLocker plugin to PAS.
''' 

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import os
from Products.CMFCore.utils import getToolByName
from Products.ZenUtils.AccountLocker.AccountLocker import manage_addAccountLocker


PLUGIN_ID = 'account_locker_plugin'
PLUGIN_TITLE = 'Lock an account after numerous failed login attempts'

class AddAccountLocker(Migrate.Step):

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):
        
        app = dmd.getPhysicalRoot()
        zport = app.zport
    
        app_acl = getToolByName(app, 'acl_users')
        zport_acl = getToolByName(zport, 'acl_users')

        context_interfaces = {app_acl:('IAuthenticationPlugin', 'IAnonymousUserFactoryPlugin'),
                    zport_acl:('IAuthenticationPlugin',)}

        for context in context_interfaces:
            manage_addAccountLocker(context, PLUGIN_ID, PLUGIN_TITLE)
        log.info("Plugin %s is added", PLUGIN_ID)
  

        for context, interfaces in context_interfaces.iteritems():
            activatePluginForInterfaces(context, PLUGIN_ID, interfaces)
        log.info("Plugin %s activated for %s interfaces", PLUGIN_ID, context_interfaces)


        for context in context_interfaces:
            movePluginToTop(context, PLUGIN_ID, 'IAuthenticationPlugin')
        log.info("Plugin %s moved on top for IAuthenticationPlugin", PLUGIN_ID)
        

AddAccountLocker()


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

