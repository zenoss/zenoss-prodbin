#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceOrganizer

$Id: DeviceOrganizer.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import types

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from AccessControl import Permissions as permissions

from Organizer import Organizer
from DeviceManagerBase import DeviceManagerBase

from MaintenanceWindow import OrganizerMaintenanceWindow

from Products.ZenRelations.RelSchema import *

class DeviceOrganizer(Organizer, DeviceManagerBase):
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
                , 'name'          : 'Manage'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : ('Manage DMD',)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
         },
        )

    _relations =  (
        ("maintenanceWindows",
         ToManyCont(ToOne, "MaintenanceWindow", "productionState")),
        ("adminRoles", ToManyCont(ToOne,"AdministrativeRole","managedObject")),
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


    def setProdState(self, state):
        """Set production state of all devices in this Organizer.
        """
        [ d.setProdState(state) for d in self.getSubDevices() ]

    
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


    security.declareProtected('Change Organizer',
                              'manage_addMaintenanceWindow')
    def manage_addMaintenanceWindow(self, newId=None, REQUEST=None):
        "Add a Maintenance Window to this device"
        if newId:
            mw = OrganizerMaintenanceWindow(newId)
            self.maintenanceWindows._setObject(newId, mw)
        if REQUEST:
            if newId:
                REQUEST['message'] = "Maintenace Window Added"
            return self.callZenScreen(REQUEST)
                          

    security.declareProtected('Change Device', 'manage_deleteMaintenanceWindow')
    def manage_deleteMaintenanceWindow(self, maintenanceIds=(), REQUEST=None):
        "Delete a Maintenance Window to this device"
        import types
        if type(maintenanceIds) in types.StringTypes:
            maintenanceIds = [maintenanceIds]
        for id in maintenanceIds:
            self.maintenanceWindows._delObject(id)
        if REQUEST:
            if maintenanceIds:
                REQUEST['message'] = "Maintenace Window Deleted"
            return self.callZenScreen(REQUEST)
                          

    security.declareProtected('Change Device', 'manage_addAdministrativeRole')
    def manage_addAdministrativeRole(self, newId=None, REQUEST=None):
        "Add a Admin Role to this device"
        from AdministrativeRole import DevOrgAdministrativeRole
        us = None
        if newId:
            us = self.ZenUsers.getUserSettings(newId)
        if us:
            ar = DevOrgAdministrativeRole(newId)
            if us.defaultAdminRole:
                ar.role = us.defaultAdminRole
                ar.level = us.defaultAdminLevel
            self.adminRoles._setObject(newId, ar)
            ar = self.adminRoles._getOb(newId)
            ar.userSetting.addRelation(us)
        if REQUEST:
            if us:
                REQUEST['message'] = "Administrative Role Added"
            return self.callZenScreen(REQUEST)


    def manage_editAdministrativeRoles(self, ids=(), role=(), level=(), REQUEST=None):
        """Edit list of admin roles.
        """
        if type(ids) in types.StringTypes:
            ids = [ids]
            role = [role]
            level = [level]
        for i, id in enumerate(ids):
            ar = self.adminRoles._getOb(id)
            if ar.role != role[i]: ar.role = role[i]
            if ar.level != level[i]: ar.level = level[i]
        if REQUEST:
            REQUEST['message'] = "Administrative Roles Updated"
            return self.callZenScreen(REQUEST)
        

    security.declareProtected('Change Device','manage_deleteAdministrativeRole')
    def manage_deleteAdministrativeRole(self, delids=(), REQUEST=None):
        "Delete a admin role to this device"
        if type(delids) in types.StringTypes:
            delids = [delids]
        for id in delids:
            self.adminRoles._delObject(id)
        if REQUEST:
            if delids:
                REQUEST['message'] = "Administrative Roles Deleted"
            return self.callZenScreen(REQUEST)
                          

InitializeClass(DeviceOrganizer)

