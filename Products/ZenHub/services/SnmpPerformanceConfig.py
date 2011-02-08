###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2010 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = '''SnmpPerformanceConfig

Provides configuration to zenperfsnmp clients.
'''
import logging
log = logging.getLogger('zen.HubService.SnmpPerformanceConfig')

from Products.ZenCollector.services.config import CollectorConfigService


class SnmpPerformanceConfig(CollectorConfigService):
    def __init__(self, dmd, instance):
        deviceProxyAttributes = ('zMaxOIDPerRequest',
                                 'zSnmpMonitorIgnore',
                                 'zSnmpAuthPassword',
                                 'zSnmpAuthType',
                                 'zSnmpCommunity',
                                 'zSnmpPort',
                                 'zSnmpPrivPassword',
                                 'zSnmpPrivType',
                                 'zSnmpSecurityName',
                                 'zSnmpTimeout',
                                 'zSnmpTries',
                                 'zSnmpVer',
                                 'zSnmpCollectionInterval',
                                )
        CollectorConfigService.__init__(self, dmd, instance, 
                                        deviceProxyAttributes)

    def _filterDevice(self, device):
        include = CollectorConfigService._filterDevice(self, device)

        if getattr(device, 'zSnmpMonitorIgnore', False):
            self.log.debug("Device %s skipped because zSnmpMonitorIgnore is True",
                           device.id)
            include = False

        if not device.getManageIp():
            self.log.debug("Device %s skipped because its management IP address is blank.",
                           device.id)
            include = False

        return include

    def _getComponentConfig(self, comp, perfServer, oids):
        """
        SNMP components can build up the actual OID based on a base OID and
        the snmpindex of the component.
        """
        if comp.snmpIgnore():
            return None

        basepath = comp.rrdPath()
        for templ in comp.getRRDTemplates():
            for ds in templ.getRRDDataSources("SNMP"):
                if not ds.enabled or not ds.oid:
                    continue

                oid = ds.oid
                snmpindex = getattr(comp, "ifindex", comp.snmpindex)
                if snmpindex:
                    oid = "%s.%s" % (oid, snmpindex)
                oid = oid.strip('.')

                if not oid:
                    log.warn("The data source %s OID is blank -- ignoring",
                             ds.id)
                    continue

                for dp in ds.getRRDDataPoints():
                    # Everything under ZenModel *should* use titleOrId but it doesn't
                    cname = comp.viewName() if comp.meta_type != "Device" else dp.id
                    oidData = (cname,
                                 "/".join((basepath, dp.name())),
                                 dp.rrdtype,
                                 dp.getRRDCreateCommand(perfServer).strip(),
                                 dp.rrdmin, dp.rrdmax)

                    # An OID can appear in multiple data sources/data points
                    oids.setdefault(oid, []).append(oidData)

        return comp.getThresholdInstances('SNMP')

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)

        proxy.configCycleInterval = self._prefs.perfsnmpCycleInterval
        proxy.cycleInterval = getattr(device, 'zSnmpCollectionInterval', 300)
        proxy.name = device.id
        proxy.device = device.id
        proxy.lastmodeltime = device.getLastChangeString()
        proxy.lastChangeTime = float(device.getLastChange())

        proxy.snmpConnInfo = device.getSnmpConnInfo()

        # Gather the datapoints to retrieve
        perfServer = device.getPerformanceServer()
        proxy.oids = {}
        # First for the device....
        proxy.thresholds = self._getComponentConfig(device, perfServer, proxy.oids)
        # And now for its components
        for comp in device.os.getMonitoredComponents(collector="zenperfsnmp"):
            threshs = self._getComponentConfig(comp, perfServer, proxy.oids)
            if threshs:
                proxy.thresholds.extend(threshs)

        return proxy
