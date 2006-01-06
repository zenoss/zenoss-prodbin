#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################


from Hardware import Hardware

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from DateTime import DateTime

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Exceptions import *


class DeviceHW(Hardware):

    meta_type = "DeviceHW"

    totalMemory = 0L

    _properties = Hardware._properties + (
        {'id':'totalMemory', 'type':'long', 'mode':'w'},
    )

    _relations = Hardware._relations + (
        ("cpus", ToManyCont(ToOne, "CPU", "hw")),
        ("cards", ToManyCont(ToOne, "ExpansionCard", "hw")),
        ("harddisks", ToManyCont(ToOne, "HardDisk", "hw")),
    )

    security = ClassSecurityInfo()

    def __init__(self):
        id = "hw"
        Hardware.__init__(self, id)

    
    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()



InitializeClass(DeviceHW)
