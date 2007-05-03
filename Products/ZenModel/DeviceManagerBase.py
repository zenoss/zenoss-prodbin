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

class DeviceManagerBase:
    """
    Default implementation of IDeviceManager interface.  This interface
    is implemented by classes that have a device relationship to allow them
    to manage their device relations.
    """

    def deviceMoveTargets(self):
        """see IManageDevice"""
        raise NotImplementedError

    def getDeviceMoveTarget(self, moveTargetName):
        """see IManageDevice"""
        return self.getDmdRoot(self.dmdRootName).getOrganizer(moveTargetName)


    def moveDevices(self, moveTarget, deviceNames=None, REQUEST=None):
        """see IManageDevice"""
        if not moveTarget or not deviceNames: return self()
        if type(deviceNames) == types.StringType: deviceNames = (deviceNames,)
        target = self.getDeviceMoveTarget(moveTarget)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            self.devices.removeRelation(dev)
            target.devices.addRelation(dev)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())
    

    def removeDevices(self, deviceNames=None, REQUEST=None):
        """see IManageDevice"""
        if not deviceNames: return self()
        if type(deviceNames) in types.StringTypes: deviceNames = (deviceNames,)
        for devname in deviceNames:
            self.devices._delObject(devname)
        if REQUEST: return self()


    def setGroups(self, groupPaths=None, deviceNames=None, REQUEST=None):
        """ Provide a method to set device groups from any organizer """
        if not groupPaths or not deviceNames: return self()
        if type(deviceNames) == type(''): deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.setGroups(groupPaths)
        if REQUEST: REQUEST['RESPONSE'].redirect(self.getPrimaryUrlPath())

    def setSystems(self, systemPaths=None, deviceNames=None, REQUEST=None):
        """ Provide a method to set device systems from any organizer """
        if not systemPaths or not deviceNames: return self()
        if type(deviceNames) == types.StringType: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.setSystems(systemPaths)
        if REQUEST: return self()

    def setLocation(self, locationPath=None, deviceNames=None, REQUEST=None):
        """ Provide a method to set device location from any organizer """
        if not locationPath or not deviceNames: return self()
        if type(deviceNames) == types.StringType: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.setLocation(locationPath)
        if REQUEST: return self()


    def unlockDevices(self, deviceNames=None, REQUEST=None):
        """Unlock devices"""
        if not deviceNames: return self()
        if type(deviceNames) in types.StringTypes: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.unlock()
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def lockDevicesFromDeletion(self, deviceNames=None, sendEventWhenBlocked=None, REQUEST=None):
        """Lock devices from being deleted"""
        if not deviceNames: return self()
        if type(deviceNames) in types.StringTypes: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.lockFromDeletion(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def lockDevicesFromUpdates(self, deviceNames=None, sendEventWhenBlocked=None, REQUEST=None):
        """Lock devices from being deleted or updated"""
        if not deviceNames: return self()
        if type(deviceNames) in types.StringTypes: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.lockFromUpdates(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)