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
#! /usr/bin/env python 

from PerformanceConfig import PerformanceConfig

class SnmpPerfConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        return self.config.getDevices(devices)


    def remote_getDeviceUpdates(self, devices):
        return self.config.getDeviceUpdates(devices)


    def getDeviceConfig(self, device):
        return device.getSnmpOidTargets()


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateDeviceConfig', config)


    def update(self, object):
        from Products.ZenModel.RRDDataSource import RRDDataSource
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'SNMP':
                return

        PerformanceConfig.update(self, object)
