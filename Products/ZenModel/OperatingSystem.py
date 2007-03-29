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

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from ZenStatus import ZenStatus
from ZenDate import ZenDate
from Exceptions import *

from IpInterface import manage_addIpInterface
from WinService import manage_addWinService
from IpService import manage_addIpService
from OSProcess import manage_addOSProcess
from IpRouteEntry import manage_addIpRouteEntry
from FileSystem import manage_addFileSystem


class OperatingSystem(Software):

    totalSwap = 0L
    uname = ""

    _properties = Software._properties + (
        {'id':'totalSwap', 'type':'long', 'mode':'w'},
        {'id':'uname', 'type':'string', 'mode':''},
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

    def totalSwapString(self):
        return self.totalSwap and convToUnits(self.totalSwap) or 'unknown'

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


    def device(self):
        """Return our Device object for DeviceResultInt.
        """
        return self.getPrimaryParent()

    def addIpInterface(self, id, REQUEST=None):
        """Add an IpInterface.
        """
        manage_addIpInterface(self.interfaces, id)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self._getOb(id).absolute_url())

    def addWinService(self, id, REQUEST=None):
        """Add an WinService.
        """
        manage_addWinService(self.winservices, id)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self._getOb(id).absolute_url())

    def addOSProcess(self, id, className, userCreated, REQUEST=None):
        """Add an OSProcess.
        """
        manage_addOSProcess(self.processes, id, className)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self._getOb(id).absolute_url())
                
    def addIpService(self, 
                    id, 
                    protocol, 
                    port, 
                    userCreated, 
                    REQUEST=None):
        """Add an IpInterface.
        """
        manage_addIpService(self.ipservices, 
                            id, 
                            protocol, 
                            port, 
                            userCreated=userCreated)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.ipservices._getOb(id).absolute_url())

    def addFileSystem(self, id, REQUEST=None):
        """Add an FileSystem.
        """
        manage_addFileSystem(self.filesystems, id)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self._getOb(id).absolute_url())
        
    def addIpRouteEntry(self, 
                        dest, 
                        nexthopid, 
                        interface, 
                        routeproto, 
                        routetype, 
                        userCreated, 
                        REQUEST=None):
        """Add an IpRouteEntry.
        """
        manage_addIpRouteEntry(self.routes, 
                                dest, 
                                nexthopid, 
                                interface, 
                                routeproto, 
                                routetype, 
                                userCreated=userCreated)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.absolute_url())
        
InitializeClass(OperatingSystem)
