##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals

from itertools import ifilter
from zope import component
from Acquisition import aq_base
from twisted.internet import defer, reactor
from ZODB.transact import transact
from PerformanceConfig import PerformanceConfig
from Products.ZenHub.PBDaemon import translateError
from Products.DataCollector.DeviceProxy import DeviceProxy
from Products.DataCollector.Plugins import loadPlugins
from Products.ZenEvents import Event
from Products.ZenCollector.interfaces import IConfigurationDispatchingFilter
from Products.ZenUtils.events import pausedAndOptimizedIndexing
import time
import logging
log = logging.getLogger('zen.ModelerService')

class ModelerService(PerformanceConfig):

    plugins = None

    def __init__(self, dmd, instance):
        PerformanceConfig.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)

    def createDeviceProxy(self, dev, skipModelMsg=''):
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
        result.skipModelMsg = skipModelMsg

        if not skipModelMsg:
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
            result.temp_device = dev.isTempDevice()
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
    def remote_getDeviceConfig(self, names, checkStatus=False):
        result = []
        for name in names:
            device = self.getPerformanceMonitor().findDevice(name)
            if not device:
                continue
            device = device.primaryAq()
            skipModelMsg = ''

            if device.isLockedFromUpdates():
                skipModelMsg = "device %s is locked, skipping modeling" % device.id
                self.dmd.ZenEventManager.sendEvent({
                    'device': device.id,
                    'severity': Event.Warning,
                    'component': 'zenmodeler',
                    'eventClass': '/Status/Update',
                    'summary': skipModelMsg,
                })

            if checkStatus and (device.getPingStatus() > 0
                                or device.getSnmpStatus() > 0):
                skipModelMsg = "device %s is down skipping modeling" % device.id
            if (device.productionState <
                device.getProperty('zProdStateThreshold', 0)):
                skipModelMsg = "device %s is below zProdStateThreshold" % device.id
            if skipModelMsg:
                log.info(skipModelMsg)

            result.append(self.createDeviceProxy(device, skipModelMsg))
        return result

    @translateError
    def remote_getDeviceListByMonitor(self, monitor=None):
        if monitor is None:
            monitor = self.instance
        monitor = self.dmd.Monitors.Performance._getOb(monitor)
        return [d.id for d in monitor.devices.objectValuesGen()]

    def _getOptionsFilter(self, options):
        deviceFilter = lambda x: True
        if options:
            dispatchFilterName = options.get('configDispatch', '') if options else ''
            filterFactories = dict(component.getUtilitiesFor(IConfigurationDispatchingFilter))
            filterFactory = filterFactories.get(dispatchFilterName, None) or \
                            filterFactories.get('', None)
            if filterFactory:
                deviceFilter = filterFactory.getFilter(options) or deviceFilter
        return deviceFilter

    @translateError
    def remote_getDeviceListByOrganizer(self, organizer, monitor=None, options=None):
        if monitor is None:
            monitor = self.instance
        filter = self._getOptionsFilter(options)
        root = self.dmd.Devices.getOrganizer(organizer)
        #If getting all devices for a monitor, get them from the monitor
        if root.getPrimaryId() == '/zport/dmd/Devices':
            monitor = self.dmd.Monitors.Performance._getOb(monitor)
            devices = ((d.id, d.snmpLastCollection) for d in ifilter(filter, monitor.devices.objectValuesGen()))
        else:
            devices= ((d.id, d.snmpLastCollection) for d in ifilter(filter, root.getSubDevicesGen())
                if d.getPerformanceServerName() == monitor)
        return [d[0] for d in sorted(devices, key=lambda x:x[1])]

    @translateError
    def remote_applyDataMaps(self, device, maps, devclass=None, setLastCollection=False):
        from Products.DataCollector.ApplyDataMap import ApplyDataMap
        device = self.getPerformanceMonitor().findDevice(device)
        adm = ApplyDataMap(self)
        adm.setDeviceClass(device, devclass)
        def inner(map):
            def action():
                start_time = time.time()
                completed= bool(adm._applyDataMap(device, map, commit=False))
                end_time=time.time()-start_time
                if hasattr(map, "relname"):
                    log.debug("Time in _applyDataMap for Device %s with relmap %s objects: %.2f", device.getId(),map.relname,end_time)
                elif hasattr(map,"modname"):
                    log.debug("Time in _applyDataMap for Device %s with objectmap, size of %d attrs: %.2f",device.getId(),len(map.items()),end_time)
                else:
                    log.debug("Time in _applyDataMap for Device %s: %.2f . Could not find if relmap or objmap",device.getId(),end_time)
                return completed
            return self._do_with_retries(action)

        changed = False
        with pausedAndOptimizedIndexing():
            for map in maps:
                result = inner(map)
                changed = changed or result

        if setLastCollection:
            self._setSnmpLastCollection(device)

        return changed

    def _setSnmpLastCollection(self, device):
        transactional = transact(device.setSnmpLastCollection)
        return self._do_with_retries(transactional)

    @translateError
    def remote_setSnmpLastCollection(self, device):
        device = self.getPerformanceMonitor().findDevice(device)
        self._setSnmpLastCollection(device)

    def _do_with_retries(self, action):
        from ZODB.POSException import StorageError
        max_attempts = 3
        for attempt_num in range(max_attempts):
            try:
                return action()
            except StorageError as e:
                if attempt_num == max_attempts-1:
                    msg = "{0}, maximum retries reached".format(e)
                else:
                    msg = "{0}, retrying".format(e)
                log.info(msg)


    @transact
    @translateError
    def remote_setSnmpConnectionInfo(self, device, version, port, community):
        device = self.getPerformanceMonitor().findDevice(device)
        device.updateDevice(zSnmpVer=version,
                            zSnmpPort=port,
                            zSnmpCommunity=community)

    def pushConfig(self, device):
        from twisted.internet.defer import succeed
        return succeed(device)


if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    tester = ServiceTester(ModelerService)

    def configprinter(config):
        print "%s (%s) Plugins" % (config.id, config.manageIp)
        print sorted(x.pluginName for x in config.plugins)

    def showDeviceInfo():
        if tester.options.device:
            name = tester.options.device
            config = tester.service.remote_getDeviceConfig([name])
            if config:
                print "Config for %s =" % name
                configprinter(config[0])
            else:
                log.warn("No configs found for %s", name)
        else:
            collector = tester.options.monitor
            devices = tester.service.remote_getDeviceListByMonitor(collector)
            devices = sorted(devices)
            print "Device list = %s" % devices

    showDeviceInfo()
