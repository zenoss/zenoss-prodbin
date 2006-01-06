#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

import logging

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

    totalSwap = 0L

    _properties = Software._properties + (
        {'id':'totalSwap', 'type':'long', 'mode':'w'},
    )

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
        self._delObject("os")   # OperatingSystem is a software 
                                # but doens't have os relationship


    def traceRoute(self, target, ippath):
        """Trace the route to target using our routing table.
        """
        logging.debug("device %s target %s", self.getDeviceName(), target)
        nextdev = None
        for route in self.getRouteObjs():
            ip = route.getNextHopIp()
            logging.debug("target %s next hop %s", route.getTarget(), ip)
            if ip == target:
                ippath.append(ip)
                return ippath
            if route.matchTarget(target):
                nextdev = route.getNextHopDevice()
                break
        else:
            logging.debug("device %s default route", self.getDeviceName())
            ip = ""
            default = self.routes._getOb("0.0.0.0_0", None)
            if default:
                ip = default.getNextHopIp()
                nextdev = default.getNextHopDevice()
        if ip == "0.0.0.0":
            ippath.append(target)
            return ippath
        if nextdev: 
            ippath.append(ip)
            return nextdev.traceRoute(target, ippath)
        raise TraceRouteGap("unable to trace to %s, gap at %s" % (target, 
                            self.getDeviceName()))


    def getRouteObjs(self):
        """Return our real route objects.
        """
        return filter(lambda r: getattr(r, "_targetobj",False), self.routes())


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
            int = self.interfaces._getOb(intname, None)
            if int: return int
        for int in self.interfaces():
            if int.ipaddresses.countObjects():
                return int

    
    security.declareProtected('View', 'getDeviceInterfaceByIndex')
    def getInterfaceByIndex(self, ifindex):
        """Return an interface based on its snmp index.
        """
        idxmap = getattr(aq_base(self), "_v_idxmap", {})
        if not idxmap:
            for i in self.interfaces.objectValuesAll():
                idxmap[i.ifindex] = i
            self._v_idxmap = idxmap
        return idxmap.get(ifindex, None)


    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()


InitializeClass(OperatingSystem)
