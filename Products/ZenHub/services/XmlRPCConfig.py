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

class XmlRPCConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        return self.config.getDevices(devices)


    def remote_getDeviceUpdates(self, devices):
        return self.config.getDeviceUpdates(devices)


    def remote_getXmlRpcDevices(self, *args, **kwargs):
        return self.config.getXmlRpcDevices(*args, **kwargs)


    def getDeviceConfig(self, device):
        return device.getXmlRpcTargets()


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateDeviceConfig', config)

