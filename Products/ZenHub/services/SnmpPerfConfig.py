###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from PerformanceConfig import PerformanceConfig

from sets import Set
from ZODB.POSException import POSError



class SnmpPerfConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        """Return information for snmp collection on all devices."""
        if devices:
            if not isinstance(devices, list):
                devices = Set([devices])
            else:
                devices = Set(devices)
        snmp = []
        for dev in self.config.devices():
            if devices and dev.id not in devices: continue
            dev = dev.primaryAq()
            try:
                targets = dev.getSnmpOidTargets()
                if targets:
                    snmp.append(targets)
            except POSError: raise
            except:
                self.log.exception("device %s", dev.id)
        return snmp

    def remote_getDeviceUpdates(self, devices):
        """Return a list of devices that have changed.
        Takes a list of known devices and the time of last known change.
        The result is a list of devices that have changed,
        or not in the list."""
        lastChanged = dict(devices)
        new = Set()
        all = Set()
        for dev in self.config.devices():
            dev = dev.primaryAq()
            if dev.snmpMonitorDevice():
                all.add(dev.id)
                if lastChanged.get(dev.id, 0) < float(dev.getLastChange()):
                    new.add(dev.id)
        deleted = Set(lastChanged.keys()) - all
        return list(new | deleted)

    def getDeviceConfig(self, device):
        "Template method helper for PerformanceConfig.pushConfig"
        return device.getSnmpOidTargets()


    def sendDeviceConfig(self, listener, config):
        "Template method helper for PerformanceConfig.pushConfig"
        return listener.callRemote('updateDeviceConfig', config)


    def update(self, object):
        from Products.ZenModel.RRDDataSource import RRDDataSource
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'SNMP':
                return

        PerformanceConfig.update(self, object)
