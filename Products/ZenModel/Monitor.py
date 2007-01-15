#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

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
