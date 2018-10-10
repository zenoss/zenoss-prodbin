##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

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
