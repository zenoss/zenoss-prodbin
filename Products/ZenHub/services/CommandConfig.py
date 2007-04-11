#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

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
        
