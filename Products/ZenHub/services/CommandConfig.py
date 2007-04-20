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

class CommandConfig(PerformanceConfig):

    def remote_getDataSourceCommands(self, *args, **kwargs):
        return self.config.getDataSourceCommands(*args, **kwargs)


    def getDeviceConfig(self, device):
        return device.getDataSourceCommands()


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateConfig', config)


    def update(self, object):
        from Products.ZenModel.RRDDataSource import RRDDataSource
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'COMMAND':
                return

        PerformanceConfig.update(self, object)
        
