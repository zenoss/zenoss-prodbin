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
from ZODB.POSException import POSError

class CommandConfig(PerformanceConfig):

    def remote_getDataSourceCommands(self, devices = None):
        return self.getDataSourceCommands(devices)


    def getDeviceConfig(self, device):
        return device.getDataSourceCommands()


    def sendDeviceConfig(self, listener, config):
        return listener.callRemote('updateConfig', config)


    def getDataSourceCommands(self, devices = None):
        '''Get the command configuration for all devices.
        '''
        result = []
        for dev in self.config.devices():
            if devices and dev.id not in devices: continue
            dev = dev.primaryAq()
            try:
                cmdinfo = dev.getDataSourceCommands()
                if not cmdinfo: continue
                result.append(cmdinfo)
            except POSError: raise
            except:
                self.log.exception("device %s", dev.id)
        return result

    def update(self, object):
        from Products.ZenModel.RRDDataSource import RRDDataSource
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'COMMAND':
                return

        PerformanceConfig.update(self, object)
        
