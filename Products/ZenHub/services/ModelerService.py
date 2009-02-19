###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Acquisition import aq_base

from PerformanceConfig import PerformanceConfig
from Products.ZenHub.PBDaemon import translateError
from Products.DataCollector.DeviceProxy import DeviceProxy

from Products.DataCollector.Plugins import loadPlugins

import logging
log = logging.getLogger('zen.ModelerService')

class ModelerService(PerformanceConfig):

    plugins = None

    def __init__(self, dmd, instance):
        PerformanceConfig.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)
        self.methodPriorityMap = {
            'applyDataMaps': 0.75,
            }

    def createDeviceProxy(self, dev):
        if self.plugins is None:
            self.plugins = {}
            for loader in loadPlugins(self.dmd):
                try:
                    plugin = loader.create()
                    plugin.loader = loader
                    self.plugins[plugin.name()] = plugin
                except Exception, ex:
                    log.exception(ex)
    
        result = DeviceProxy()
        result.id = dev.getId()
        if not dev.manageIp:
            dev.setManageIp()
        result.manageIp = dev.manageIp
        result.plugins = []
        for name in dev.zCollectorPlugins:
            plugin = self.plugins.get(name, None)
            log.debug('checking plugin %s for device %s' % (name, dev.getId()))
            if plugin and plugin.condition(dev, log):
                log.debug('adding plugin %s for device %s' % (name,dev.getId()))
                result.plugins.append(plugin.loader)
                plugin.copyDataToProxy(dev, result)
        return result

    @translateError
    def remote_getClassCollectorPlugins(self):
        result = []
        for dc in self.dmd.Devices.getSubOrganizers():
            localPlugins = getattr(aq_base(dc), 'zCollectorPlugins', False)
            if not localPlugins: continue
            result.append((dc.getOrganizerName(), localPlugins))
        return result

    @translateError
    def remote_getDeviceConfig(self, names):
        result = []
        for name in names:
            device = self.getPerformanceMonitor().findDevice(name)
            if not device:
                continue
            device = device.primaryAq()
            if (device.productionState <
                getattr(device, 'zProdStateThreshold', 0)):
                continue
            result.append(self.createDeviceProxy(device))
        return result

    @translateError
    def remote_getDeviceListByMonitor(self, monitor=None):
        if monitor is None:
            monitor = self.instance
        monitor = self.dmd.Monitors.Performance._getOb(monitor)
        return [d.id for d in monitor.devices.objectValuesGen()]
    
    @translateError
    def remote_getDeviceListByOrganizer(self, organizer, monitor=None):
        if monitor is None:
            monitor = self.instance
        root = self.dmd.Devices.getOrganizer(organizer)
        return [d.id for d in root.getSubDevicesGen() \
            if d.getPerformanceServerName() == monitor]

    @translateError
    def remote_applyDataMaps(self, device, maps, devclass=None):
        from Products.DataCollector.ApplyDataMap import ApplyDataMap
        device = self.getPerformanceMonitor().findDevice(device)

        adm = ApplyDataMap(self)
        changed = False
        for map in maps:
            if adm._applyDataMap(device, map):
                changed = True

        if devclass and devclass != device.getDeviceClassPath():
            device.moveDevices(devclass,device.id)
            changed = True
            
        if changed:
            device.setLastChange()
            import transaction
            trans = transaction.get()
            trans.setUser("datacoll")
            trans.note("data applied from automated collection")
            trans.commit()
        return changed

    @translateError
    def remote_setSnmpLastCollection(self, device):
        device = self.getPerformanceMonitor().findDevice(device)
        device.setSnmpLastCollection()
        from transaction import commit
        commit()
        
        
        
    def pushConfig(self, device):
        from twisted.internet.defer import succeed
        return succeed(device)
