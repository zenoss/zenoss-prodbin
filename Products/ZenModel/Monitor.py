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

__doc__="""Monitor

Base class for all Monitor or Monitor Configuration Classes.  This is
an abstract class that is used for the devices to monitors
relationship which says which monitors monitor which devices.

$Id: Monitor.py,v 1.5 2004/04/14 22:11:48 edahl Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import InitializeClass

from ZenModelRM import ZenModelRM
from DeviceManagerBase import DeviceManagerBase

class Monitor(ZenModelRM, DeviceManagerBase):
    meta_type = 'Monitor'
    
    def breadCrumbs(self, target='dmd'):
        bc = ZenModelRM.breadCrumbs(self)
        return [bc[0],bc[-1]]

    def deviceMoveTargets(self):
        """see IManageDevice"""
        mroot = self.getDmdRoot("Monitors")._getOb(self.monitorRootName)
        return filter(lambda x: x != self.id, mroot.objectIds())
           

    def getDeviceMoveTarget(self, moveTargetName):
        """see IManageDevice"""
        mroot = self.getDmdRoot("Monitors")._getOb(self.monitorRootName)
        return mroot._getOb(moveTargetName)

    
    def getOrganizerName(self):
        """Return the DMD path of an Organizer without its dmdSubRel names."""
        return self.id

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
        if deviceNames is None:
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


InitializeClass(Monitor)
