#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""Device

Device is a base class that represents the idea of a single compter
system that is made up of software running on hardware.  It currently
must be IP enabled but maybe this will change.

$Id: Device.py,v 1.121 2004/04/23 19:11:58 edahl Exp $"""

__version__ = "$Revision: 1.121 $"[11:-2]

import time

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from DateTime import DateTime
from App.Dialogs import MessageDialog

from Products.CMFCore import permissions

from Products.ZenUtils.Utils import zenpathsplit, zenpathjoin

from Exceptions import DeviceExistsError
from Instance import Instance
from DeviceResultInt import DeviceResultInt
from PingStatusInt import PingStatusInt
from CricketDevice import CricketDevice
from ZenStatus import ZenStatus
from ZenDate import ZenDate

CopyError='Copy Error'

from logging import debug, info, warn, critical, exception

def manage_createDevice(context, deviceName, devicePath="", 
            tag="", serialNumber="",
            snmpCommunity="public", snmpPort=161,
            rackSlot=0, productionState=1000, comments="",
            manufacturer="", model="", 
            locationPath="", rack="",
            groupPaths=[], systemPaths=[],
            statusMonitors=["localhost"], cricketMonitor="localhost",
            REQUEST = None):

    "Device factory creates a device and sets up its relations"        

    if context.getOrganizer("Devices").findDevice(deviceName):
        raise DeviceExistsError, "Device %s already exists" % deviceName
    if not devicePath:
        devicePath = "/Devices/Unknown"
        loginInfo = {}
        loginInfo['snmpCommunity'] = snmpCommunity
        loginInfo['snmpPort'] = snmpPort
        cEntry = context.getOrganizer("Devices").myClassifier.classifyDevice(
                                    deviceName, loginInfo)
        if cEntry:
            devicePath = cEntry.getDeviceClassPath
            manufacturer = manufacturer and manufacturer \
                           or cEntry.getManufacturer
            model = model and model or cEntry.getProduct
   
    deviceClass = context.getOrganizer("Devices").getDeviceClass(devicePath)
    device = deviceClass.createInstance(deviceName)
    device.manage_editDevice(
                tag, serialNumber,
                snmpCommunity, snmpPort,
                rackSlot, productionState, comments,
                manufacturer, model,
                locationPath, rack, 
                groupPaths, systemPaths,
                statusMonitors, cricketMonitor)
    return device


def classifyDevice(context, deviceName, devicePath, 
                snmpCommunity, snmpPort, loginName, loginPassword):
    """get a device if devicePath is None try classifier"""
    return devicePath



def manage_addDevice(context, id, REQUEST = None):
    """make a device"""
    serv = Device(id)
    context._setObject(serv.id, serv)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addDevice = DTMLFile('dtml/addDevice',globals())

    
class Device(Instance, PingStatusInt, DeviceResultInt, CricketDevice):
    """Device object"""

    portal_type = meta_type = 'Device'
    
    default_catalog = "deviceSearch" #device ZCatalog

    relationshipManagerPathRestriction = '/Devices'

    _properties = (
                    {'id':'pingStatus', 'type':'int', 
                        'mode':'w', 'setter':'setPingStatus'},
                    {'id':'snmpStatus', 'type':'int', 
                        'mode':'w', 'setter':'setSnmpStatus'},
                    {'id':'productionState', 'type':'keyedselection', 
                       'mode':'w', 'select_variable':'getProdStateConversions',
                       'setter':'setProdState'},
                    {'id':'tag', 'type':'string', 'mode':'w'},
                    {'id':'serialNumber', 'type':'string', 'mode':'w'},
                    {'id':'snmpPort', 'type':'int', 'mode':'w'},
                    {'id':'snmpCommunity', 'type':'string', 'mode':'w'},
                    {'id':'snmpAgent', 'type':'string', 'mode':'w'},
                    {'id':'snmpDescr', 'type':'string', 'mode':''},
                    {'id':'snmpOid', 'type':'string', 'mode':''},
                    {'id':'snmpUpTime', 'type':'int', 'mode':''},
                    {'id':'snmpContact', 'type':'string', 'mode':''},
                    {'id':'snmpSysName', 'type':'string', 'mode':''},
                    {'id':'snmpLocation', 'type':'string', 'mode':''},
                    {'id':'snmpLastCollection', 'type':'Date', 'mode':''},
                    {'id':'osVersion', 'type':'string', 'mode':'w'},
                    {'id':'rackSlot', 'type':'int', 'mode':'w'},
                    {'id':'comments', 'type':'text', 'mode':'w'},
                    {'id':'cpuType', 'type':'string', 'mode':'w'},
                    {'id':'totalMemory', 'type':'float', 'mode':'w'},
                   ) 
   
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'Device',
            'meta_type'      : 'Device',
            'description'    : """Base class for all devices""",
            'icon'           : 'Device_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDevice',
            'immediate_view' : 'viewIndex',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewDeviceStatus'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'detail'
                , 'name'          : 'Detail'
                , 'action'        : 'viewDeviceDetail'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'deviceEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'deviceHistoryEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewDevicePerformance'
                , 'permissions'   : (
                  permissions.View, )
                },                
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editDevice'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'management'
                , 'name'          : 'Management'
                , 'action'        : 'deviceManagement'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (
                  permissions.View, )
                },
            )
         },
        )

    security = ClassSecurityInfo()
    
    def __init__(self, id):
        Instance.__init__(self, id)
        self._pingStatus = ZenStatus(-1)
        self._snmpStatus = ZenStatus(-1)
        self.commandStatus = "Not Tested"
        self._v_stamp = None
        self.productionState = 1000
        self.tag = ""
        self.serialNumber = ""
        self.snmpCommunity = ""
        self.snmpAgent = ""
        self.snmpDescr = ""
        self.snmpOid = ""
        self._snmpUpTime = ZenStatus(-1)
        self.snmpContact = ""
        self.snmpSysName = ""
        self.snmpLocation = ""
        self.osVersion = ""
        self.sshVersion = ""
        self.rackSlot = 0
        self.comments = ""
        self.snmpPort = 161
        self._snmpLastCollection = ZenDate('1968/1/8')
        self.cpuType = ""
        self.totalMemory = 0.0

    
    def __getattr__(self, name):
        if name == 'datacenter':
            return self.getDataCenter()
        elif name == 'pingStatus':
            return self._pingStatus.getStatus()
        elif name == 'snmpStatus':
            return self._snmpStatus.getStatus()
        elif name == 'snmpUpTime':
            return self._snmpUpTime.getStatus()
        elif name == 'snmpLastCollection':
            return self._snmpLastCollection.getDate()
        else:
            raise AttributeError, name


    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'pingStatus':
            self.setPingStatus(value)
        elif id == 'snmpStatus':
            self.setSnmpStatus(value)
        elif id == 'snmpLastCollection':
            self.setSnmpLastCollection(value)
        else:    
            setattr(self,id,value)


    security.declareProtected('View', 'getLocationName')
    def getLocationName(self):
        """return the full location name ie /Location/SubLocation/Rack"""
        loc = self.location()
        if loc: return loc.getLocationName()
        return ""


    security.declareProtected('View', 'getModelName')
    def getModelName(self):
        model = self.model()
        if model: return model.getId()
        return ''


    security.declareProtected('View', 'getManufacturer')
    def getManufacturer(self):
        if self.model():
            return self.model().manufacturer()
  

    security.declareProtected('View', 'getManufacturerName')
    def getManufacturerName(self):
        manuf = self.getManufacturer()
        if manuf: 
            return manuf.getId()
        return ''


    security.declareProtected('View', 'getManufacturerLink')
    def getManufacturerLink(self, target="rightFrame"):
        if self.model():
            return self.model().manufacturer.getPrimaryLink(target)
        return None


    security.declareProtected('View', 'getSystemNames')
    def getSystemNames(self):
        """get the system names for this device"""
        return map(lambda x: x.getSystemName(), self.systems())


    security.declareProtected('View', 'getDeviceGroupNames')
    def getDeviceGroupNames(self):
        """get the device group names for this device"""
        return map(lambda x: x.getDeviceGroupName(), self.groups())


    security.declareProtected('View', 'getOsVersion')
    def getOsVersion(self):
        return self.osVersion


    security.declareProtected('View', 'getStatusMonitorNames')
    def getStatusMonitorNames(self):
        """return status monitor names"""
        return map(lambda x: x.getId(), self.monitors())

    
    security.declareProtected('View', 'getCricketServer')
    def getCricketServer(self):
        """return device cricket server"""
        return self.cricket()


    security.declareProtected('View', 'getCricketServer')
    def getCricketServerName(self):
        """return device cricket server"""
        cr = self.cricket()
        if cr: return cr.getId()
        return ''


    security.declareProtected('View', 'getLastSnmpCollection')
    def getSnmpLastCollection(self):
        return self._snmpLastCollection.getDate()

    
    security.declareProtected('View', 'getLastSnmpCollectionString')
    def getSnmpLastCollectionString(self):
        return self._snmpLastCollection.getString()


    security.declareProtected('View', 'getManageInterface')
    def getManageInterface(self):
        """return the management interface of a device looks first
        for manageInterfaceNames in aquisition path if not found
        uses default 'Loopback0' and 'Ethernet0' if none of these are found
        returns the first interface if there is any"""
        if hasattr(self, 'zManageInterfaceNames'):
            intnames = self.manageInterfaceNames
        else:
            intnames = ('Loopback0', 'Ethernet0', 'hme0', 'ge0', 'eth0')
        for intname in intnames:
            if hasattr(self.interfaces, intname):
                return self.interfaces._getOb(intname)
        ints = self.interfaces()
        if len(ints):
            return ints[0]

    
    security.declareProtected('View', 'getDeviceInterfaceIndexDict')
    def getDeviceInterfaceIndexDict(self):
        """build a dictionary of interfaces keyed on ifindex
        Used by SnmpCollector.CustomMaps.RouteMap to connect routes
        with interfaces"""
        dict = {}
        for i in self.interfaces.objectValuesAll():
            dict[i.ifindex] = i
        return dict


    security.declareProtected('View', 'uptimeStr')
    def uptimeStr(self):
        '''return a textual representation of the snmp uptime'''
        if self.snmpUpTime < 0:
            return "Unknown"
        elif self.snmpUpTime == 0:
            return "0d:0h:0m:0s"
        ut = self.snmpUpTime
        days = ut/8640000
        hour = (ut%8640000)/360000
        mins = ((ut%8640000)%360000)/6000
        secs = (((ut%8640000)%360000)%6000)/100.0
        return "%02dd:%02dh:%02dm:%02ds" % (
            days, hour, mins, secs)


    def getPeerDeviceClassNames(self):
        "build a list of all device paths that have the python class pyclass"
        dclass = self.getOrganizer("Devices")
        return dclass.getPeerDeviceClassNames(self.__class__)

        
        


    ####################################################################
    # Edit functions used to manage device relations and other attributes
    ####################################################################

    security.declareProtected('Change Device', 'manage_editDevice')
    def manage_editDevice(self, 
                tag="", serialNumber="",
                snmpCommunity="public", snmpPort=161,
                rackSlot=0, productionState=1000, comments="",
                manufacturer="", model="", 
                locationPath="", rack="",
                groupPaths=[], systemPaths=[],
                statusMonitors=["localhost"], cricketMonitor="localhost",
                REQUEST=None):
        """edit device relations and attributes"""
        self.tag = tag
        self.serialNumber = serialNumber
        self.snmpCommunity = snmpCommunity
        self.snmpPort = snmpPort
        self.rackSlot = rackSlot
        self.productionState = productionState
        self.comments = comments

        if manufacturer and model:
            info("setting manufacturer to %s model to %s"
                            % (manufacturer, model))
            self.setModel(manufacturer, model)

        if locationPath: 
            if rack:
                locationPath += "/%s" % rack
                info("setting rack location to %s" % locationPath)
                self.setRackLocation(locationPath)
            else:
                info("setting location to %s" % locationPath)
                self.setLocation(locationPath)

        if groupPaths: 
            info("setting group %s" % groupPaths)
            self.setGroups(groupPaths)

        if systemPaths: 
            info("setting system %s" % systemPaths)
            self.setSystems(systemPaths)

        info("setting status monitor to %s" % statusMonitors)
        self.setStatusMonitors(statusMonitors)

        info("setting cricket monitor to %s" % cricketMonitor)
        self.setCricketMonitor(cricketMonitor)
       
        if REQUEST: 
            REQUEST['message'] = "Device Saved at time:"
            return self.editDevice()


    security.declareProtected('Change Device', 'setProdState')
    def setProdState(self, state):
        self.productionState = int(state)


    security.declareProtected('Change Device', 'setSnmpLastCollection')
    def setSnmpLastCollection(self, value=None):
        self._snmpLastCollection.setDate(value)


    security.declareProtected('Change Device', 'addManufacturer')
    def addManufacturer(self, newManufacturerName, REQUEST=None):
        """add a manufacturer to the database"""
        self.getOrganizer("Companies").getCompany(newManufacturerName)
        if REQUEST:
            REQUEST['manufacturer'] = newManufacturerName
            REQUEST['message'] = ("Added Manufacturer %s at time:" 
                                    % newManufacturerName)
            return self.editDevice()


    security.declareProtected('Change Device', 'setModel')
    def setModel(self, manufacturer, model, newModelName="", REQUEST=None):
        """set the model of this device"""
        if newModelName: model = newModelName
        modelObj = self.getOrganizer("Products").getModelProduct(
                                        manufacturer, model)
        self.addRelation("model", modelObj)
        if REQUEST:
            REQUEST['message'] = ("Set Manufacturer %s and Model %s at time:" 
                                    % (manufacturer, model))
            return self.editDevice()


    security.declareProtected('Change Device', 'setRackLocation')
    def setRackLocation(self, locationPath, newLocationPath=None, REQUEST=None):
        """set a the locaiton of a device within a rack
        if the location ends with '-3' it will be the
        rackslot of the device"""
        if newLocationPath: locationPath = newLocationPath
        locobj = self.getOrganizer("Locations").getRackLoaction(locationPath)
        self.addRelation("location", locobj)
        if REQUEST:
            REQUEST['message'] = "Set RackLocation %s at time:" % locationPath
            return self.editDevice()

    
    security.declareProtected('Change Device', 'setLocation')
    def setLocation(self, locationPath, newLocationPath=None, REQUEST=None):
        """set the location of a device within a generic location path"""
        if newLocationPath: locationPath = newLocationPath
        locobj = self.getOrganizer("Locations").getLocation(locationPath)
        self.addRelation("location", locobj)
        if REQUEST:
            REQUEST['message'] = "Set Location %s at time:" % locationPath
            return self.editDevice()


    security.declareProtected('Change Device', 'setCricketMonitor')
    def setCricketMonitor(self, cricketMonitor,
                            newCricketMonitor=None, REQUEST=None):
        """set the cricket monitor for this device if newCricketMonitor
        is passed in create it"""
        if newCricketMonitor: cricketMonitor = newCricketMonitor
        obj = self.getOrganizer("Monitors").getCricketMonitor(
                                                    cricketMonitor)
        self.addRelation("cricket", obj)
        if REQUEST:
            REQUEST['message'] = "Set Cricket %s at time:" % cricketMonitor
            return self.editDevice()


    security.declareProtected('Change Device', 'setStatusMonitors')
    def setStatusMonitors(self, statusMonitors):
        objGetter = self.getOrganizer("Monitors").getStatusMonitor
        self._setRelations("monitors", objGetter, statusMonitors)


    security.declareProtected('Change Device', 'addStatusMonitor')
    def addStatusMonitor(self, newStatusMonitor, REQUEST=None):
        """add new status monitor to the database and this device"""
        mon = self.getOrganizer("Monitors").getStatusMonitor(newStatusMonitor)
        self.addRelation("monitors", mon)
        if REQUEST:
            REQUEST['message'] = "Added Monitor %s at time:" % newStatusMonitor
            return self.editDevice()


    security.declareProtected('Change Device', 'setGroups')
    def setGroups(self, groupPaths):
        """set the list of groups for this device based on a list of paths"""
        objGetter = self.getOrganizer("Groups").getDeviceGroup
        self._setRelations("groups", objGetter, groupPaths)


    security.declareProtected('Change Device', 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """add a device group to the database and this device"""
        group = self.getOrganizer("Groups").getDeviceGroup(newDeviceGroupPath)
        self.addRelation("groups", group)
        if REQUEST:
            REQUEST['message'] = "Added Group %s at time:" % newDeviceGroupPath
            return self.editDevice()


    security.declareProtected('Change Device', 'setSystems')
    def setSystems(self, systemPaths):
        """set a list of systems to this device using their system paths"""
        objGetter = self.getOrganizer("Systems").getSystem
        self._setRelations("systems", objGetter, systemPaths)
      

    security.declareProtected('Change Device', 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """add a systems to this device using its system path"""
        sys = self.getOrganizer("Systems").getSystem(newSystemPath)
        self.addRelation("systems", sys)
        if REQUEST:
            REQUEST['message'] = "Added System %s at time:" % newSystemPath
            return self.editDevice()


    security.declareProtected('Change Device', 'setTerminalServer')
    def setTerminalServer(self, termservername):
        termserver = self.findDevice(termservername)
        if termserver:
            self.addRelation('termserver', termserver)


    def _setRelations(self, relName, objGetter, relPaths):
        """set related objects to this device"""
        if type(relPaths) != type([]) and type(relPaths) != type(()):
            relPaths = [relPaths,]
        relPaths = filter(lambda x: x.strip(), relPaths)
        rel = getattr(self, relName, None)
        if not rel: 
            raise AttributeError, "Relation %s not found" % relName
        curRelIds = {}
        for value in rel.objectValuesAll():
            curRelIds[value.getPathName()] = value
        for path in relPaths:
            if not curRelIds.has_key(path):
                robj = objGetter(path)
                self.addRelation(relName, robj)
            else:
                del curRelIds[path]
        for obj in curRelIds.values():
            self.removeRelation(relName, obj)


    ####################################################################
    # Private getter functions that implement DeviceResultInt
    ####################################################################

    security.declareProtected('View', 'getDevice')
    def getDevice(self):
        """support DeviceResultInt mixin class"""
        return self


    def _getSnmpStatusNumber(self):
        '''get a device's raw snmp status number'''
        return self._snmpStatus.getStatus()


    security.declareProtected('View', 'getSnmpStatus')
    def _getSnmpStatus(self):
        '''get a device's snmp status and perform conversion'''
        return self._snmpStatus.getStatusString()


    security.declareProtected('View', 'getSnmpStatusColor')
    def _getSnmpStatusColor(self):
        '''get the device's snmp status color'''
        return self._snmpStatus.color()


    def _getDeviceName(self):
        '''Return the device name id'''
        return self.getId()


    def _getDeviceClassPath(self):
        '''Return the device class'''
        return self.deviceClass().getDeviceClassPath()


    def _getProdState(self):
        '''Return the production state of the device'''
        return self.convertProdState(self.productionState)

    
    ####################################################################
    # Status Management Functions used by status monitors
    ####################################################################


    security.declareProtected('Manage Device Status', 'resetPingStatus')
    def resetSnmpStatus(self):
        '''reset device's snmp status to zero'''
        self._snmpStatus.reset()


    security.declareProtected('Manage Device Status', 'incrSnmpStatus')
    def incrSnmpStatus(self):
        '''increment a device's snmp status by one'''
        self._snmpStatus.incr()


    security.declareProtected('Manage Device Status', 'setSetSnmp')
    def setSnmpStatus(self, value):
        """set snmp status"""
        self._snmpStatus.setStatus(value)


    security.declareProtected('Manage Device Status', 'setSnmpUpTime')
    def setSnmpUpTime(self, value):
        """set the value of the snmpUpTime status object"""
        self._snmpUpTime.setStatus(value)


    def snmpAgeCheck(self, hours):
        lastcoll = self.getSnmpLastCollection()
        hours = hours/24.0
        if DateTime() > lastcoll + hours: return 1


    #need to decuple these two methods out to actions
    security.declareProtected('View', 'deviceEvents')
    def deviceEvents(self):
        """get the event list of this object"""
        self.REQUEST.set('ev_whereclause', "Node = '%s'"%self.id)
        return self.viewEvents(self.REQUEST)


    security.declareProtected('View', 'deviceHistoryEvents')
    def deviceHistoryEvents(self):
        """get the history event list of this object"""
        self.REQUEST.set('ev_whereclause', "Node = '%s'"%self.id)
        self.REQUEST.set('ev_orderby', "LastOccurrence desc")
        return self.viewHistoryEvents(self.REQUEST)


    ####################################################################
    # Management Functions
    ####################################################################

    security.declareProtected('Change Device', 'collectConfig')
    def collectConfig(self, REQUEST=None):
        """collect the configuration of this device"""
        from Products.SnmpCollector.SnmpCollector import SnmpCollector
        sc = SnmpCollector(noopts=1,app=self.getPhysicalRoot())
        if REQUEST:
            response = REQUEST.RESPONSE
            sc.setLoggingStream(response)
        try:
            sc.collectDevice(self)
        except:
            exception('exception while collecting snmp for device %s'
                              %  self.getId())
        else:
            info('collected snmp information for device %s'
                            % self.getId())



    security.declareProtected('Change Device', 'deleteDevice')
    def deleteDevice(self, REQUEST=None):
        """Delete device from the DMD"""
        parent = self.getParent()
        parent._delObject(self.getId())
        if REQUEST is not None:
            # FIXME I need to fill the rightFrame but don't!!!
            REQUEST['RESPONSE'].redirect(parent.absolute_url() + 
                                            "/viewDeviceClassOverview")


    security.declareProtected('View', 'summary')
    def summary(self):
        """build text summery of object for indexing"""
        return (self.id + " " + 
                self.tag + " " +
                self.serialNumber + " " +
                self.snmpDescr + " " +
                self.snmpContact + " " +
                self.snmpLocation + " " +
                self.osVersion)
  
InitializeClass(Device)
