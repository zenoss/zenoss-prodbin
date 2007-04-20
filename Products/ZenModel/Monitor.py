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


InitializeClass(Monitor)
