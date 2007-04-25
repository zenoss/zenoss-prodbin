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

class ProcessConfig(PerformanceConfig):

    def remote_getOSProcessConf(self, devices=None):
        return self.config.getOSProcessConf(devices)

    def remote_getProcessStatus(self, devices=None):
        return self.config.getProcessStatus(devices)

    def getDeviceConfig(self, device):
        return device.getOSProcessConf()

    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateDevice', config)



