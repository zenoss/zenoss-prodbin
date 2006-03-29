#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

import logging
log = logging.getLogger("zen.OS")

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
        ("winservices", ToManyCont(ToOne, "WinService", "os")),
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


    def __call__(self, REQUEST=None):
        pp = self.getPrimaryParent()
        screen = getattr(pp, "deviceOsDetail", False)
        if not screen: return pp()
        return screen()


    def traceRoute(self, target, ippath):
        """Trace the route to target using our routing table.
        """
        log.debug("device %s target %s", self.getDeviceName(), target)
        nextdev = None
        for route in self.getRouteObjs():
            ip = route.getNextHopIp()
            log.debug("target %s next hop %s", route.getTarget(), ip)
            if ip == target:
                ippath.append(ip)
                return ippath
            if route.matchTarget(target):
                nextdev = route.getNextHopDevice()
                break
        else:
            log.debug("device %s default route", self.getDeviceName())
            ip = ""
            default = self.routes._getOb("0.0.0.0_0", None)
            if default:
                ip = default.getNextHopIp()
                nextdev = default.getNextHopDevice()
        if nextdev == self.device() or ip=="0.0.0.0":
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
        return filter(lambda r: r.target(), self.routes())


    security.declareProtected('View', 'getInterfaceByIndex')
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
