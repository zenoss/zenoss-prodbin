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

import types
from ZenossSecurity import ZEN_VIEW

class DeviceManagerBase:
    """
    Default implementation of IDeviceManager interface.  This interface
    is implemented by classes that have a device relationship to allow them
    to manage their device relations.
    """

    def getDevices(self):
        return [ dev for dev in self.devices() 
                    if self.checkRemotePerm(ZEN_VIEW, dev)]
                    
    def deviceMoveTargets(self):
        """see IManageDevice"""
        raise NotImplementedError
    
    def removeDevices(self, deviceNames=None, deleteStatus=False, 
                      deleteHistory=False, deletePerf=False,REQUEST=None):
        """see IManageDevice"""
        from Products.ZenUtils.Utils import unused
        unused(deleteHistory, deletePerf, deleteStatus)
        if not deviceNames: return self()
        if type(deviceNames) in types.StringTypes: deviceNames = (deviceNames,)
        for devname in deviceNames:
            self.devices._delObject(devname)
        if REQUEST:
            return self()
