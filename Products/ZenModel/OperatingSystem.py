#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

import logging
log = logging.getLogger("zen.OS")

import types

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

from Products.ZenUtils.Utils import prepId

class OperatingSystem(Software):

    totalSwap = 0L
    uname = ""

    _properties = Software._properties + (
        {'id':'totalSwap', 'type':'long', 'mode':'w'},
        {'id':'uname', 'type':'string', 'mode':''},
    )

    _relations = Software._relations + (
        ("interfaces", ToManyCont(ToOne, "Products.ZenModel.IpInterface", "os")),
        ("routes", ToManyCont(ToOne, "Products.ZenModel.IpRouteEntry", "os")),
        ("ipservices", ToManyCont(ToOne, "Products.ZenModel.IpService", "os")),
        ("winservices", ToManyCont(ToOne, "Products.ZenModel.WinService", "os")),
        ("processes", ToManyCont(ToOne, "Products.ZenModel.OSProcess", "os")),
        ("filesystems", ToManyCont(ToOne, "Products.ZenModel.FileSystem", "os")),
        ("software", ToManyCont(ToOne, "Products.ZenModel.Software", "os")),
    )

    security = ClassSecurityInfo()

    routeTypeMap = ('other', 'invalid', 'direct', 'indirect')
    routeProtoMap = ('other', 'local', 'netmgmt', 'icmp',
            'egp', 'ggp', 'hello', 'rip', 'is-is', 'es-is',
            'ciscoIgrp', 'bbnSpfIgrp', 'ospf', 'bgp')
            
    factory_type_information = (
        {
            'id'             : 'Device',
            'meta_type'      : 'Device',
            'description'    : """Base class for all devices""",
            'icon'           : 'Device_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDevice',
            'immediate_view' : 'deviceOsDetail',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : '../deviceStatus'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'osdetail'
                , 'name'          : 'OS'
                , 'action'        : 'deviceOsDetail'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'hwdetail'
                , 'name'          : 'Hardware'
                , 'action'        : '../deviceHardwareDetail'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'swdetail'
                , 'name'          : 'Software'
                , 'action'        : '../deviceSoftwareDetail'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : '../viewEvents'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : '../viewHistoryEvents'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'perfServer'
                , 'name'          : 'Perf'
                , 'action'        : '../viewDevicePerformance'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : '../viewHistory'
                , 'permissions'   : (permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : '../editDevice'
                , 'permissions'   : ("Change Device",)
                },
            )
         },
        )


    def __init__(self):
        id = "os"
        Software.__init__(self, id)
        self._delObject("os")   # OperatingSystem is a software 
                                # but doens't have os relationship


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

    def deleteDeviceComponents(self, context, componentNames=[], REQUEST=None):
        """Delete device components"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.manage_deleteComponent()
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def unlockDeviceComponents(self, context, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Unlock device components"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.unlock(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)
            
    def lockDeviceComponentsFromDeletion(self, context, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock device components from deletion"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.lockFromDeletion(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def lockDeviceComponentsFromUpdates(self, context, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock device components from updates"""
        if not componentNames: return self()
        if type(componentNames) in types.StringTypes: componentNames = (componentNames,)
        for componentName in componentNames:
            dc = context._getOb(componentName)
            dc.lockFromUpdates(sendEventWhenBlocked)
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def addIpInterface(self, id, userCreated, REQUEST=None):
        """Add IpInterfaces.
        """
        manage_addIpInterface(self.interfaces, id, userCreated)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.interfaces._getOb(id).absolute_url())
    
    def deleteIpInterfaces(self, componentNames=[], REQUEST=None):
        """Delete IpInterfaces"""
        return self.deleteDeviceComponents(self.interfaces, componentNames, REQUEST)

    def unlockIpInterfaces(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Unlock IpInterfaces"""
        return self.unlockDeviceComponents(self.interfaces, componentNames, sendEventWhenBlocked, REQUEST)

    def lockIpInterfacesFromDeletion(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpInterfaces from deletion"""
        return self.lockDeviceComponentsFromDeletion(self.interfaces, componentNames, sendEventWhenBlocked, REQUEST)

    def lockIpInterfacesFromUpdates(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpInterfaces from updates"""
        return self.lockDeviceComponentsFromUpdates(self.interfaces, componentNames, sendEventWhenBlocked, REQUEST)


    def addWinService(self, 
                        id, 
                        description,
                        userCreated, 
                        REQUEST=None):
        """Add an WinService.
        """
        manage_addWinService(self.winservices, 
                                id, 
                                description,
                                userCreated=userCreated)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.winservices._getOb(id).absolute_url())

    def deleteWinServices(self, componentNames=[], REQUEST=None):
        """Delete WinServices"""
        return self.deleteDeviceComponents(self.winservices, componentNames, REQUEST)

    def unlockWinServices(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Unlock WinServices"""
        return self.unlockDeviceComponents(self.winservices, componentNames, sendEventWhenBlocked, REQUEST)

    def lockWinServicesFromDeletion(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock WinServices from deletion"""
        return self.lockDeviceComponentsFromDeletion(self.winservices, componentNames, sendEventWhenBlocked, REQUEST)

    def lockWinServicesFromUpdates(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock WinServices from updates"""
        return self.lockDeviceComponentsFromUpdates(self.winservices, componentNames, sendEventWhenBlocked, REQUEST)


    def addOSProcess(self, 
                        id, 
                        className, 
                        userCreated, 
                        REQUEST=None):
        """Add an OSProcess.
        """
        manage_addOSProcess(self.processes, 
                            id, 
                            className, 
                            userCreated)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.processes._getOb(id).absolute_url())

    def deleteOSProcesses(self, componentNames=[], REQUEST=None):
        """Delete OSProcesses"""
        return self.deleteDeviceComponents(self.processes, componentNames, REQUEST)

    def unlockOSProcesses(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Unlock OSProcesses"""
        return self.unlockDeviceComponents(self.processes, componentNames, sendEventWhenBlocked, REQUEST)

    def lockOSProcessesFromDeletion(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock OSProcesses from deletion"""
        return self.lockDeviceComponentsFromDeletion(self.processes, componentNames, sendEventWhenBlocked, REQUEST)

    def lockOSProcessesFromUpdates(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock OSProcesses from updates"""
        return self.lockDeviceComponentsFromUpdates(self.processes, componentNames, sendEventWhenBlocked, REQUEST)


    def addIpService(self, 
                    id, 
                    protocol, 
                    port, 
                    userCreated, 
                    REQUEST=None):
        """Add IpServices.
        """
        manage_addIpService(self.ipservices, 
                            id, 
                            protocol, 
                            port, 
                            userCreated=userCreated)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.ipservices._getOb(id).absolute_url())

    def deleteIpServices(self, componentNames=[], REQUEST=None):
        """Delete IpServices"""
        return self.deleteDeviceComponents(self.ipservices, componentNames, REQUEST)

    def unlockIpServices(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Unlock IpServices"""
        return self.unlockDeviceComponents(self.ipservices, componentNames, sendEventWhenBlocked, REQUEST)

    def lockIpServicesFromDeletion(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpServices from deletion"""
        return self.lockDeviceComponentsFromDeletion(self.ipservices, componentNames, sendEventWhenBlocked, REQUEST)

    def lockIpServicesFromUpdates(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpServices from updates"""
        return self.lockDeviceComponentsFromUpdates(self.ipservices, componentNames, sendEventWhenBlocked, REQUEST)


    def addFileSystem(self, id, userCreated, REQUEST=None):
        """Add a FileSystem.
        """
        fsid = prepId(id)
        manage_addFileSystem(self.filesystems, id, userCreated)
        if REQUEST is not None:
            REQUEST['RESPONSE'].redirect(self.filesystems._getOb(fsid).absolute_url())

    def deleteFileSystems(self, componentNames=[], REQUEST=None):
        """Delete FileSystems"""
        return self.deleteDeviceComponents(self.filesystems, componentNames, REQUEST)

    def unlockFileSystems(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Unlock FileSystems"""
        return self.unlockDeviceComponents(self.filesystems, componentNames, sendEventWhenBlocked, REQUEST)

    def lockFileSystemsFromDeletion(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock FileSystems from deletion"""
        return self.lockDeviceComponentsFromDeletion(self.filesystems, componentNames, sendEventWhenBlocked, REQUEST)

    def lockFileSystemsFromUpdates(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock FileSystems from updates"""
        return self.lockDeviceComponentsFromUpdates(self.filesystems, componentNames, sendEventWhenBlocked, REQUEST)


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

    def deleteIpRouteEntries(self, componentNames=[], REQUEST=None):
        """Delete IpRouteEntries"""
        return self.deleteDeviceComponents(self.routes, componentNames, REQUEST)

    def unlockIpRouteEntries(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Unlock IpRouteEntries"""
        return self.unlockDeviceComponents(self.routes, componentNames, sendEventWhenBlocked, REQUEST)

    def lockIpRouteEntriesFromDeletion(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpRouteEntries from deletion"""
        return self.lockDeviceComponentsFromDeletion(self.routes, componentNames, sendEventWhenBlocked, REQUEST)

    def lockIpRouteEntriesFromUpdates(self, componentNames=[], sendEventWhenBlocked=None, REQUEST=None):
        """Lock IpRouteEntries from updates"""
        return self.lockDeviceComponentsFromUpdates(self.routes, componentNames, sendEventWhenBlocked, REQUEST)

InitializeClass(OperatingSystem)
