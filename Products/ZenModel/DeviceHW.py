#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################


from Hardware import Hardware

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from DateTime import DateTime

from AccessControl import Permissions as permissions

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from Exceptions import *


class DeviceHW(Hardware):

    meta_type = "DeviceHW"

    totalMemory = 0L

    _properties = Hardware._properties + (
        {'id':'totalMemory', 'type':'long', 'mode':'w'},
    )

    _relations = Hardware._relations + (
        ("cpus", ToManyCont(ToOne, "Products.ZenModel.CPU", "hw")),
        ("cards", ToManyCont(ToOne, "Products.ZenModel.ExpansionCard", "hw")),
        ("harddisks", ToManyCont(ToOne, "Products.ZenModel.HardDisk", "hw")),
    )

    security = ClassSecurityInfo()

    def __init__(self):
        id = "hw"
        Hardware.__init__(self, id)

    
    def __call__(self, REQUEST=None):
        pp = self.getPrimaryParent()
        screen = getattr(pp, "deviceHardwareDetail", False)
        if not screen: return pp()
        return screen()

    def totalMemoryString(self):
        return self.totalMemory and convToUnits(self.totalMemory) or 'unknown' 

    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()



InitializeClass(DeviceHW)
