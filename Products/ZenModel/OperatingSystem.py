#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################


from Software import Software

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Acquisition import aq_base
from DateTime import DateTime

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from ZenStatus import ZenStatus
from ZenDate import ZenDate
from Exceptions import *


class OperatingSystem(Software):

    _relations = Software._relations + (
        ("interfaces", ToManyCont(ToOne, "IpInterface", "os")),
        ("routes", ToManyCont(ToOne, "IpRouteEntry", "os")),
        ("ipservices", ToManyCont(ToOne, "IpService", "os")),
        ("processes", ToManyCont(ToOne, "OSProcess", "os")),
        ("filesystems", ToManyCont(ToOne, "FileSystem", "os")),
        ("software", ToManyCont(ToOne, "Software", "os")),
    )

    security = ClassSecurityInfo()
    
    def __init__(self):
        id = "os"
        Software.__init__(self, id)


    security.declareProtected('View', 'getManageInterface')
    def getManageInterface(self):
        """
        Return the management interface of a device looks first
        for zManageInterfaceNames in aquisition path if not found
        uses default 'Loopback0' and 'Ethernet0' if none of these are found
        returns the first interface if there is any.
        """
        intnames = getattr(self, 'zManageInterfaceNames')
        for intname in intnames:
            if hasattr(self.interfaces, intname):
                return self.interfaces._getOb(intname)
        ints = self.interfaces()
        if len(ints):
            return ints[0]

    
    security.declareProtected('View', 'getDeviceInterfaceIndexDict')
    def getInterfaceIndexDict(self):
        """
        Build a dictionary of interfaces keyed on ifindex
        Used by SnmpCollector.CustomMaps.RouteMap to connect routes
        with interfaces.
        """
        dict = {}
        for i in self.interfaces.objectValuesAll():
            dict[i.ifindex] = i
        return dict


    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()


InitializeClass(OperatingSystem)
