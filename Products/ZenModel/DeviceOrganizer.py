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
import re

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from AccessControl import Permissions as permissions
from Acquisition import aq_parent

from Organizer import Organizer
from DeviceManagerBase import DeviceManagerBase
from Commandable import Commandable
from ZenMenuable import ZenMenuable
from MaintenanceWindowable import MaintenanceWindowable
from AdministrativeRoleable import AdministrativeRoleable

from Products.AdvancedQuery import MatchRegexp, Eq, Or, In

from Products.ZenRelations.RelSchema import *
import simplejson

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
        return [d for d in self.getSubDevices()
                if deviceNames is None or d.getPrimaryId() in deviceNames]


    def setProdState(self, state, deviceNames=None, 
                        isOrganizer=False, REQUEST=None):
        """Set production state of all devices in this Organizer.
        """
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.setProdState(state)
        if REQUEST:
            statename = self.convertProdState(state)
            REQUEST['message'] = "Production State set to %s" % statename
            return self.callZenScreen(REQUEST)

            
    def setPriority(self, priority, deviceNames=None, 
                    isOrganizer=False, REQUEST=None):
        """Set prioirty of all devices in this Organizer.
        """
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.setPriority(priority)
        if REQUEST:
            priname = self.convertPriority(priority)
            REQUEST['message'] = "Priority set to %s" % priname 
            return self.callZenScreen(REQUEST)

    
    def setStatusMonitors(self, statusMonitors=None, deviceNames=None, 
                                isOrganizer=False, REQUEST=None):
        """ Provide a method to set status monitors from any organizer """
        if not statusMonitors:
            if REQUEST: REQUEST['message'] = "No Monitor Selected"
            return self.callZenScreen(REQUEST)
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.setStatusMonitors(statusMonitors)
        if REQUEST: 
            REQUEST['message'] = "Status monitor set to %s" % (
                                    statusMonitors)
            return self.callZenScreen(REQUEST)


    def setPerformanceMonitor(self, performanceMonitor=None, deviceNames=None, 
                                isOrganizer=False, REQUEST=None):
        """ Provide a method to set performance monitor from any organizer """
        if not performanceMonitor:
            if REQUEST: REQUEST['message'] = "No Monitor Selected"
            return self.callZenScreen(REQUEST)
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.setPerformanceMonitor(performanceMonitor)
        if REQUEST: 
            REQUEST['message'] = "Performance monitor set to %s" % (
                                    performanceMonitor)
            return self.callZenScreen(REQUEST)
  

    def setGroups(self, groupPaths=None, deviceNames=None, 
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device groups from any organizer """
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        if not groupPaths: groupPaths = []
        for dev in self._buildDeviceList(deviceNames):
            dev.setGroups(groupPaths)
        if REQUEST: 
            REQUEST['message'] = "Groups set to %s" % ", ".join(groupPaths)
            return self.callZenScreen(REQUEST)


    def setSystems(self, systemPaths=None, deviceNames=None, 
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device systems from any organizer """
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        if not systemPaths: systemPaths = []
        for dev in self._buildDeviceList(deviceNames):
            dev.setSystems(systemPaths)
        if REQUEST: 
            REQUEST['message'] = "Systems set to %s" % ", ".join(systemPaths)
            return self.callZenScreen(REQUEST)

    def setLocation(self, locationPath="", deviceNames=None,
                    isOrganizer=False, REQUEST=None):
        """ Provide a method to set device location from any organizer """
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.setLocation(locationPath)
        if REQUEST: 
            REQUEST['message'] = "Location set to %s" % locationPath
            return self.callZenScreen(REQUEST)

    def unlockDevices(self, deviceNames=None, isOrganizer=False, REQUEST=None):
        """Unlock devices"""
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.unlock()
        if REQUEST:
            REQUEST['message'] = "Devices unlocked"
            return self.callZenScreen(REQUEST)

    def lockDevicesFromDeletion(self, deviceNames=None, 
                    sendEventWhenBlocked=None, isOrganizer=False, REQUEST=None):
        """Lock devices from being deleted"""
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.lockFromDeletion(sendEventWhenBlocked)
        if REQUEST:
            REQUEST['message'] = "Devices locked from deletion"
            return self.callZenScreen(REQUEST)

    def lockDevicesFromUpdates(self, deviceNames=None, 
                sendEventWhenBlocked=None, isOrganizer=False, REQUEST=None):
        """Lock devices from being deleted or updated"""
        if deviceNames is None and not isOrganizer:
            if REQUEST: REQUEST['message'] = "No Devices Selected"
            return self.callZenScreen(REQUEST)
        for dev in self._buildDeviceList(deviceNames):
            dev.lockFromUpdates(sendEventWhenBlocked)
        if REQUEST:
            REQUEST['message'] = "Devices locked from updates and deletion"
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


    def getAdvancedQueryDeviceList(self, offset=0, count=50, filter='',
                                   orderby='id', orderdir='asc'):
        catalog = getattr(self, self.default_catalog)
        filter = '(?is).*%s.*' % filter
        filterquery = Or(
            MatchRegexp('id', filter),
            MatchRegexp('getDeviceIp', filter),
            MatchRegexp('getProdState', filter),
            MatchRegexp('getDeviceClassPath', filter)
        )
        query = Eq('getPhysicalPath', self.absolute_url_path()
                    ) & filterquery
        objects = catalog.evalAdvancedQuery(query, ((orderby, orderdir),))
        objects = list(objects)
        totalCount = len(objects)
        offset, count = int(offset), int(count)
        return totalCount, objects[offset:offset+count] 


    def getJSONDeviceInfo(self, offset=0, count=50, filter='',
                          orderby='id', orderdir='asc'):
        """yo"""
        totalCount, devicelist = self.getAdvancedQueryDeviceList(
                offset, count, filter, orderby, orderdir)
        results = [x.getObject().getDataForJSON() + ['odd'] 
                   for x in devicelist]
        return simplejson.dumps((results, totalCount))


    def getDeviceBatch(self, selectstatus='none', goodevids=[],
                       badevids=[], offset=0, count=50, filter='',
                       orderby='id', orderdir='asc'):
        if not isinstance(goodevids, (list, tuple)):
            goodevids = [goodevids]
        if not isinstance(badevids, (list, tuple)):
            badevids = [badevids]
        if selectstatus=='all':
            idquery = ~In('id', badevids)
        else:
            idquery = In('id', goodevids)
        query = Eq('getPhysicalPath', self.absolute_url_path()) & idquery
        catalog = getattr(self, self.default_catalog)
        objects = catalog.evalAdvancedQuery(query)
        return [x['id'] for x in objects]


InitializeClass(DeviceOrganizer)

