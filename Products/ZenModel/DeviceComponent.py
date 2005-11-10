#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Device Component

All device components inherit from this class

$Id: DeviceComponent.py,v 1.1 2004/04/06 21:05:03 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from ZenModelRM import ZenModelRM
from ManagedEntity import ManagedEntity
from CricketView import CricketView


class DeviceComponent(ZenModelRM, ManagedEntity, CricketView):
    
    portal_type = meta_type = "DeviceComponent"

    security = ClassSecurityInfo()

    def __init__(self, id, title=None):
        ZenModelRM.__init__(self, id)
        self._cricketTargetMap = {}
        self._cricketTargetPath = ''


    def getParentDeviceName(self):
        """return the name of this component's device"""
        name = ""
        dev = self.device()
        if dev: name = dev.getDeviceName()
        return name
       

    def getParentDeviceUrl(self):
        """return the url of this component's device"""
        url = ""
        dev = self.device()
        if dev: url = dev.absolute_url()
        return url
    
    
    def getStatus(self, statClass):
        """Return the status number for this component of class statClass.
        """
        return self.getEventManager().getComponentStatus(
                self.getParentDeviceName(), self.id, statclass=statClass)
                                        



InitializeClass(DeviceComponent)
