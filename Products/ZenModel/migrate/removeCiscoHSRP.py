###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """
    The zenoss.snmp.CiscoHSRP modeler plugin was broken several versions ago
    when the zenmodeler daemon was converted to a PBDaemon. This migrate script
    removes references to the modeler plugin from the system.
    """

import logging
log = logging.getLogger('zen.migrate')

import Migrate

def removeModelerPlugin(obj, plugin_name):
    if not obj.hasProperty('zCollectorPlugins'):
        return

    plugins = obj.zCollectorPlugins
    if 'zenoss.snmp.CiscoHSRP' in plugins:
        log.info("Removing zenoss.snmp.CiscoHSRP modeler plugin from %s",
            obj.titleOrId())
        pluginsList = list(plugins)
        pluginsList.remove('zenoss.snmp.CiscoHSRP')
        obj.zCollectorPlugins = tuple(pluginsList)


class RemoveCiscoHSRP(Migrate.Step):
    version = Migrate.Version(2, 6, 0)

    def cutover(self, dmd):
        plugin_name = 'zenoss.snmp.CiscoHSRP'

        # Remove the plugin from all device classes.
        removeModelerPlugin(dmd.Devices, plugin_name)

        for device_class in dmd.Devices.getSubOrganizers():
            removeModelerPlugin(device_class, plugin_name)

        # Remove the plugin from all devices.
        for device in dmd.Devices.getSubDevices():
            removeModelerPlugin(device, plugin_name)


RemoveCiscoHSRP()
