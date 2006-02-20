#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent

class WinService(OSComponent):
    """Hardware object"""
    portal_type = meta_type = 'WinService'

    acceptPause = False
    acceptStop = False
    monitored = False
    name = ""
    caption = ""
    description = ""
    pathName = ""
    serviceType = ""
    startMode = ""
    startName = ""
    
    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont, "OperatingSystem", "winservices")),
    )

    security = ClassSecurityInfo()

    def getStatus(self):
        """Return the status of this service as a number.
        """
        if not self.monitored: return -1
        return OSComponent.getStatus(self, "/Status/WinService")


InitializeClass(WinService)

