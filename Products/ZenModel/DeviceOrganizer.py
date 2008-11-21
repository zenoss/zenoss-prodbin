###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from itertools import ifilter
from types import StringTypes

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Organizer import Organizer
from DeviceManagerBase import DeviceManagerBase
from Commandable import Commandable
from ZenMenuable import ZenMenuable
from MaintenanceWindowable import MaintenanceWindowable
from AdministrativeRoleable import AdministrativeRoleable

from Products.CMFCore.utils import getToolByName

from Products.ZenRelations.RelSchema import *

from ZenossSecurity import *

from Products.ZenUtils.Utils import unused 

import logging
LOG = logging.getLogger('ZenModel.DeviceOrganizer')

class DeviceOrganizer(Organizer, DeviceManagerBase, Commandable, ZenMenuable, 
                        MaintenanceWindowable, AdministrativeRoleable):
    """
    DeviceOrganizer is the base class for device organizers.
    It has lots of methods for rolling up device statistics and information.
    """
    
    security = ClassSecurityInfo()

    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'immediate_view' : 'deviceOrganizerStatus',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
#                { 'id'            : 'historyEvents'
#                , 'name'          : 'History'
#                , 'action'        : 'viewHistoryEvents'
#                , 'permissions'   : (ZEN_VIEW, )
#                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : (ZEN_MANAGE_DMD,)
                },
            )
         },
        )

    _relations =  Organizer._relations + (
        ("maintenanceWindows", ToManyCont(
            ToOne, "Products.ZenModel.MaintenanceWindow", "productionState")),
        ("adminRoles", ToManyCont(
            ToOne,"Products.ZenModel.AdministrativeRole","managedObject")),
        ('userCommands', ToManyCont(
            ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        ('zenMenus', ToManyCont(
            ToOne, 'Products.ZenModel.ZenMenu', 'menuable')),
       ) 

    security.declareProtected(ZEN_COMMON, "getSubDevices")
    def getSubDevices(self, devfilter=None):
        """
        Get all the devices under an instance of a DeviceOrganizer
        
        @param devfilter: Filter function applied to returned list
        @type devfilter: function
        @return: Devices
        @rtype: list
        
        """
        catalog = getToolByName(self.dmd.Devices, self.dmd.Devices.default_catalog)

        if not 'path' in catalog.indexes():
            LOG.warn('Please run zenmigrate to create device path indexes.')
            return self.getSubDevices_recursive(devfilter)

        brains = catalog(path="/".join(self.getPhysicalPath()))
        devices = (b.getObject() for b in brains)
        devices = ifilter(devfilter, devices)
        devices = ifilter(lambda dev:self.checkRemotePerm(ZEN_VIEW, dev),
                          devices)
        return list(devices)

    security.declareProtected(ZEN_VIEW, "getSubDevicesGen")
    def getSubDevicesGen(self):
        """get all the devices under and instance of a DeviceGroup"""
        catalog = getToolByName(self.dmd.Devices, self.dmd.Devices.default_catalog)

        if not 'path' in catalog.indexes():
            LOG.warn('Please run zenmigrate to create device path indexes.')
            yield self.getSubDevicesGen_recursive(devfilter)

        brains = catalog(path="/".join(self.getPhysicalPath()))
        devices = (b.getObject() for b in brains)
        devices = ifilter(lambda dev:self.checkRemotePerm(ZEN_VIEW, dev),
                          devices)
        for device in devices:
            yield device

    security.declareProtected(ZEN_COMMON, "getSubDevices_recursive")
    def getSubDevices_recursive(self, devfilter=None, devrel="devices"):
        devrelobj = getattr(self, devrel, None)
        if not devrelobj:
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        devices = filter(devfilter, devrelobj())
        devices = [ dev for dev in devices
                    if self.checkRemotePerm(ZEN_VIEW, dev)]
        for subgroup in self.children(checkPerm=False):
            devices.extend(subgroup.getSubDevices_recursive(devfilter, devrel))
        return devices

    security.declareProtected(ZEN_VIEW, "getSubDevicesGen")
    def getSubDevicesGen_recursive(self, devrel="devices"):
        """get all the devices under and instance of a DeviceGroup"""
        devrelobj = getattr(self, devrel, None)
        if not devrelobj: 
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        for dev in devrelobj.objectValuesGen():
            yield dev
        for subgroup in self.children():
            for dev in subgroup.getSubDevicesGen_recursive(devrel):
                yield dev

    def getSubDevicesGenTest(self, devrel="devices"):
        """get all the devices under and instance of a DeviceGroup"""
        devices = getattr(self, devrel, None)
        if not devices: 
            raise AttributeError, "%s not found on %s" % (devrel, self.id)


    def getMonitoredComponents(self):
        """Return monitored components for devices within this DeviceOrganizer.
        """
        cmps = []
        for dev in self.getSubDevicesGen():
            cmps.extend(dev.getMonitoredComponents())
        return cmps


    def getAllCounts(self, devrel="devices"):
        """Count all devices within a device group and get the
        ping and snmp counts as well"""
        devices = getattr(self, devrel)
        pingStatus = 0
        snmpStatus = 0
        devCount = devices.countObjects()
        for dev in devices():
            if dev.getPingStatusNumber() > 0:
                pingStatus += 1
            if dev.getSnmpStatusNumber() > 0:
                snmpStatus += 1
        counts = [devCount, pingStatus, snmpStatus]
        for group in self.children():
            sc = group.getAllCounts()
            for i in range(3): counts[i] += sc[i]
        return counts


    def countDevices(self, devrel="devices"):
        """count all devices with in a device group"""
        unused(devrel)
        count = self.devices.countObjects()
        for group in self.children():
            count += group.countDevices()
        return count


    def pingStatus(self, devrel="devices"):
        """aggrigate ping status for all devices in this group and below"""
        status = self._status("Ping", devrel)
        for group in self.children():
            status += group.pingStatus()
        return status

    
    def snmpStatus(self, devrel="devices"):
        """aggrigate snmp status for all devices in this group and below"""
        status = self._status("Snmp", devrel)
        for group in self.children():
            status += group.snmpStatus()
        return status


    def _buildDeviceList(self, deviceNames):
        """Build a device list for set methods"""
        if isinstance(deviceNames, basestring):
            deviceNames = [deviceNames]
        return [d.primaryAq() for d in self.getSubDevices()
                if deviceNames is None or d.id in deviceNames 
                or d.getPrimaryId() in deviceNames]


    def deviceClassMoveTargets(self):
        """Return list of all organizers excluding our self."""
        targets = filter(lambda x: x != self.getOrganizerName(),
            self.dmd.Devices.getOrganizerNames())
        targets.sort(lambda x,y: cmp(x.lower(), y.lower()))
        return targets


    def moveDevicesToClass(self, moveTarget, deviceNames=None, REQUEST=None):
        """Move Devices from one DeviceClass to Another"""
        if deviceNames is None:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        deviceNames = [ x.split('/')[-1] for x in deviceNames ]
        return self.dmd.Devices.moveDevices(moveTarget, deviceNames, REQUEST)


    def _handleOrganizerCall(self, arg=None, deviceNames=None, \
                                isOrganizer=False, REQUEST=None, \
                                deviceMethod=None):
        """ Handle the many many methods that simply call one 
        method on device differently"""
        #check to see if we have the essentials to work with
        if not deviceMethod: return
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            devMethod = getattr(dev, deviceMethod, None)
            if devMethod and arg:
                devMethod(arg)
            elif devMethod:
                devMethod()


    def _buildReturnMessage(self, REQUEST, message, paths=None, \
                               checkPaths=False):
        """build the standard return message for the various set
        methods"""
        if checkPaths:
            if paths:
                if type(paths) not in StringTypes:
                    paths = ", ".join(paths)
                message += paths 
            else:
                message = "%s unset" % message.split(" ")[0]
                
        if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
            return message 
        else:
            return self.callZenScreen(REQUEST)


    def setProdState(self, state, deviceNames=None, 
                        isOrganizer=False, REQUEST=None):
        """Set production state of all devices in this Organizer.
        """
        self._handleOrganizerCall(state, deviceNames, isOrganizer, \
                                    REQUEST, "setProdState")
        if REQUEST:
            statename = self.convertProdState(state)
            msg = "Production State set to %s" % statename
            return self._buildReturnMessage(REQUEST, msg)
        

    def setPriority(self, priority, deviceNames=None, 
                    isOrganizer=False, REQUEST=None):
        """Set prioirty of all devices in this Organizer.
        """
        self._handleOrganizerCall(priority, deviceNames, isOrganizer, \
                                    REQUEST, "setPriority")
        if REQUEST:
            priname = self.convertPriority(priority)
            msg = "Priority set to %s" % priname 
            return self._buildReturnMessage(REQUEST, msg)

    
    def setPerformanceMonitor(self, performanceMonitor=None, deviceNames=None, 
                                isOrganizer=False, REQUEST=None):
        """ Provide a method to set performance monitor from any organizer """
        if not performanceMonitor:
            if REQUEST: REQUEST['message'] = "No Monitor Selected"
            return self.callZenScreen(REQUEST)
        self._handleOrganizerCall(performanceMonitor, deviceNames, isOrganizer, \
                                    REQUEST, "setPerformanceMonitor")
        if REQUEST: 
            msg = "Collector set to %s" % (performanceMonitor)
            return self._buildReturnMessage(REQUEST, msg)
 

    def setGroups(self, groupPaths=None, deviceNames=None, 
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device groups from any organizer """
        if not groupPaths: groupPaths = []
        self._handleOrganizerCall(groupPaths, deviceNames, isOrganizer, \
                                    REQUEST, "setGroups")
        if REQUEST:
            msg = "Groups set to"
            return self._buildReturnMessage(REQUEST, msg, groupPaths, True) 


    def setSystems(self, systemPaths=None, deviceNames=None, 
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device systems from any organizer """
        if not systemPaths: systemPaths = []
        self._handleOrganizerCall(systemPaths, deviceNames, isOrganizer, \
                                    REQUEST, "setSystems")
        if REQUEST:
            msg = "Systems set to"
            return self._buildReturnMessage(REQUEST, msg, systemPaths, True) 

    def setLocation(self, locationPath="", deviceNames=None,
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device location from any organizer """
        self._handleOrganizerCall(locationPath, deviceNames, isOrganizer, \
                                    REQUEST, "setLocation")
        if REQUEST: 
            msg = "Location set to %s" % locationPath
            return self._buildReturnMessage(REQUEST, msg)

    def unlockDevices(self, deviceNames=None, isOrganizer=False, REQUEST=None):
        """Unlock devices"""
        self._handleOrganizerCall(None, deviceNames, isOrganizer, \
                                    REQUEST, "unlock")
        if REQUEST:
            msg = "Devices unlocked"
            return self._buildReturnMessage(REQUEST, msg)

    def lockDevicesFromDeletion(self, deviceNames=None, 
                    sendEventWhenBlocked=None, isOrganizer=False, REQUEST=None):
        """Lock devices from being deleted"""
        self._handleOrganizerCall(sendEventWhenBlocked, deviceNames, isOrganizer, \
                                    REQUEST, "lockFromDeletion")
        if REQUEST:
            msg = "Devices locked from deletion"
            return self._buildReturnMessage(REQUEST, msg)

    def lockDevicesFromUpdates(self, deviceNames=None, 
                sendEventWhenBlocked=None, isOrganizer=False, REQUEST=None):
        """Lock devices from being deleted or updated"""
        self._handleOrganizerCall(sendEventWhenBlocked, deviceNames, isOrganizer, \
                                    REQUEST, "lockFromUpdates")
        if REQUEST:
            msg = "Devices locked from updates and deletion"
            return self._buildReturnMessage(REQUEST, msg)


    def index_object(self):
        """No action. 
        Index of subdevices will happen in manage_addAdministrativeRole
        """
        pass

    def unindex_object(self):
        """No action. 
        Unindex of subdevices will happen in manage_deleteAdministrativeRole
        """
        pass 

    def manage_addAdministrativeRole(self, newId, REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_addAdministrativeRole
        Adds an administrator to this DeviceOrganizer
        
        @param userid: User to make an administrator of this Organizer
        @type userid: string
        """
        AdministrativeRoleable.manage_addAdministrativeRole(self, newId)
        for dev in self.getSubDevices():
            dev = dev.primaryAq()
            dev.setAdminLocalRoles()
        if REQUEST:
            REQUEST['message'] = "Administrative Role %s added" % newId
            return self.callZenScreen(REQUEST)


    def manage_editAdministrativeRoles(self, ids=(), role=(), 
                                        level=(), REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_editAdministrativeRoles
        Edit the administrators to this DeviceOrganizer
        """
        AdministrativeRoleable.manage_editAdministrativeRoles(
                                         self,ids,role,level)
        for dev in self.getSubDevices():
            dev = dev.primaryAq()
            dev.setAdminLocalRoles()
        if REQUEST:
            REQUEST['message'] = "Administrative Roles Updated"
            return self.callZenScreen(REQUEST)
           

    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        """
        Overrides AdministrativeRoleable.manage_deleteAdministrativeRole
        Deletes administrators to this DeviceOrganizer
        
        @param delids: Users to delete from this Organizer
        @type delids: tuple of strings
        """
        AdministrativeRoleable.manage_deleteAdministrativeRole(self, delids)
        for dev in self.getSubDevices():
            dev = dev.primaryAq()
            dev.setAdminLocalRoles()
        if REQUEST:
            REQUEST['message'] = "Administrative Roles Deleted"
            return self.callZenScreen(REQUEST)


    def manage_snmpCommunity(self, REQUEST=None):
        """reset Community on all devices in this Organizer.
        """
        [ d.manage_snmpCommunity() for d in self.getSubDevices() ]
        if REQUEST:
            return self.callZenScreen(REQUEST)
    
    def setManageIp(self, REQUEST=None):
        """reset ip on all devices in this Organizer.
        """
        [ d.setManageIp() for d in self.getSubDevices() ]
        if REQUEST:
            return self.callZenScreen(REQUEST)
    
    def collectDevice(self, REQUEST=None):
        """model all devices in this Organizer.
        """
        [ d.collectDevice() for d in self.getSubDevices() ]
        if REQUEST:
            return self.callZenScreen(REQUEST)

    def _status(self, type, devrel="devices"):
        """build status info for device in this device group"""
        status = 0
        statatt = "get%sStatusNumber" % type
        devices = getattr(self, devrel, None)
        if not devices: 
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        for device in devices():
            if getattr(device, statatt, -1)() > 0:
                status += 1
        return status

    def statusColor(self, status):
        """colors for status fields for device groups"""
        retval = '#00ff00'
        if status == -1:
            retval = "#d02090"
        elif status == 1:
            retval = '#ffff00'
        elif status == 2:
            retval = '#ff9900'
        elif status > 2:
            retval = '#ff0000'
        return retval

    def getUserCommandTargets(self):
        ''' Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        '''
        return self.getSubDevices()

    def getUrlForUserCommands(self):
        return self.getPrimaryUrlPath() + '/deviceOrganizerManage'

    def getLinks(self, recursive=True):
        """ Return all Links on all interfaces on all
            Devices in this Organizer
        """
        alllinks = []
        if recursive:
            devices = self.getSubDevicesGen()
        else:
            devices = self.devices.objectValuesGen()
        for device in devices:
            alllinks.extend(list(device.getLinks()))
        return alllinks

    security.declareProtected(ZEN_VIEW, 'getIconPath')
    def getIconPath(self):
        """ Override the zProperty icon path and return a folder
        """
        return "/zport/dmd/img/icons/folder.png"

    security.declareProtected(ZEN_VIEW, 'getPrettyLink')
    def getPrettyLink(self, noicon=False, shortDesc=False):
        """ Gets a link to this object, plus an icon """
        href = self.getPrimaryUrlPath().replace('%','%%')
        linktemplate = "<a href='"+href+"' class='prettylink'>%s</a>"
        icon = ("<div class='device-icon-container'> "
                "<img class='device-icon' src='%s'/> " 
                "</div>") % self.getIconPath()
        name = self.getPrimaryDmdId()
        if noicon: icon=''
        if shortDesc: name = self.id
        rendered = icon + name
        if not self.checkRemotePerm("View", self):
            return rendered
        else:
            return linktemplate % rendered

InitializeClass(DeviceOrganizer)
