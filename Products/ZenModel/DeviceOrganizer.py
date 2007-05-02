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

__doc__="""DeviceOrganizer

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import types

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from AccessControl import Permissions as permissions

from Organizer import Organizer
from DeviceManagerBase import DeviceManagerBase
from Commandable import Commandable
from ZenMenuable import ZenMenuable
from MaintenanceWindowable import MaintenanceWindowable
from AdministrativeRoleable import AdministrativeRoleable

from Products.ZenRelations.RelSchema import *

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
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'viewHistoryEvents'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'manage'
                , 'name'          : 'Administration'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : ('Manage DMD',)
                },
            )
         },
        )

    _relations =  Organizer._relations + (
        ("maintenanceWindows",
         ToManyCont(ToOne, "Products.ZenModel.MaintenanceWindow", "productionState")),
        ("adminRoles", ToManyCont(ToOne,"Products.ZenModel.AdministrativeRole","managedObject")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 'commandable')),
        ('zenMenus', ToManyCont(
            ToOne, 'Products.ZenModel.ZenMenu', 'menuable')),
       ) 

    def getSubDevices(self, devfilter=None, devrel="devices"):
        """get all the devices under an instance of a DeviceGroup"""
        devices = getattr(self, devrel, None)
        if not devices:
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        devices = filter(devfilter, devices())
        for subgroup in self.children():
            devices.extend(subgroup.getSubDevices(devfilter, devrel))
        return devices


    def getSubDevicesGen(self, devrel="devices"):
        """get all the devices under and instance of a DeviceGroup"""
        devices = getattr(self, devrel, None)
        if not devices: 
            raise AttributeError, "%s not found on %s" % (devrel, self.id)
        for dev in devices.objectValuesGen():
            yield dev
        for subgroup in self.children():
            for dev in subgroup.getSubDevicesGen(devrel):
                yield dev


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

    def setProdState(self, state, REQUEST=None):
        """Set production state of all devices in this Organizer.
        """
        [ d.setProdState(state) for d in self.getSubDevices() ]
        if REQUEST:
            return self.callZenScreen(REQUEST)
            
    def setPriority(self, priority, REQUEST=None):
        """Set production state of all devices in this Organizer.
        """
        [ d.setPriority(priority) for d in self.getSubDevices() ]
        if REQUEST:
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


InitializeClass(DeviceOrganizer)

