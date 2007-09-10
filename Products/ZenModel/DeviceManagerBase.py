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
    
    def getDeviceClassMoveTarget(self, moveTargetName):
        """see IManageDevice"""
        return self.getDmdRoot('Devices').getOrganizer(moveTargetName)

    def moveDevicesToClass(self, moveTarget, deviceNames=None, REQUEST=None):
        """see IManageDevice"""
        deviceNames = [x.split('/')[-1] for x in deviceNames]
        return self.dmd.Devices.moveDevices(moveTarget, deviceNames, REQUEST)

    def removeDevices(self, deviceNames=None, REQUEST=None):
        """see IManageDevice"""
        if not deviceNames: return self()
        if type(deviceNames) in types.StringTypes: deviceNames = (deviceNames,)
        for devname in deviceNames:
            self.devices._delObject(devname)
        if REQUEST: return self()

    def setProdState(self, state, deviceNames=None, REQUEST=None):
        """Set production state of all devices in this Organizer.
        """
        if deviceNames is None:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.setProdState(state)
        if REQUEST:
            statename = self.convertProdState(state)
            REQUEST['message'] = "Production State set to %s" % statename
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return REQUEST['message']
            else:
                return self.callZenScreen(REQUEST)
                    
    def setPriority(self, priority, deviceNames=None, REQUEST=None):
        """Set prioirty of all devices in this Organizer."""
        if not deviceNames:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for devname in deviceNames:
            dev = self.devices._getOb(devname) 
            dev.setPriority(priority)
        if REQUEST:
            priname = self.convertPriority(priority)
            REQUEST['message'] = "Priority set to %s" % priname 
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return REQUEST['message']
            else:
                return self.callZenScreen(REQUEST)
    
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
    
    
    def setStatusMonitors(self, statusMonitors=None, deviceNames=None, REQUEST=None):
        """ Provide a method to set status monitors from any organizer """
        if not statusMonitors:
            if REQUEST: REQUEST['message'] = "No Monitor Selected"
            return self.callZenScreen(REQUEST)
        if deviceNames is None:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.setStatusMonitors(statusMonitors)
        if REQUEST: 
            REQUEST['message'] = "Status monitor set to %s" % (
                                    statusMonitors)
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return REQUEST['message']
            else:
                return self.callZenScreen(REQUEST)

    def setPerformanceMonitor(self, performanceMonitor=None, deviceNames=None, REQUEST=None):
        """ Provide a method to set performance monitor from any organizer """
        if not performanceMonitor:
            if REQUEST: REQUEST['message'] = "No Monitor Selected"
            return self.callZenScreen(REQUEST)
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev.setPerformanceMonitor(performanceMonitor)
        if REQUEST: 
            REQUEST['message'] = "Performance monitor set to %s" % (
                                    performanceMonitor)
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return REQUEST['message']
            else:
                return self.callZenScreen(REQUEST) 