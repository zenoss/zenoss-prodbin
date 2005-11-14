#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Device

Device is a base class that represents the idea of a single compter
system that is made up of software running on hardware.  It currently
must be IP enabled but maybe this will change.

$Id: Device.py,v 1.121 2004/04/23 19:11:58 edahl Exp $"""

__version__ = "$Revision: 1.121 $"[11:-2]

import time
import logging

# base classes for device
from ZenModelRM import ZenModelRM
from DeviceResultInt import DeviceResultInt
from ManagedEntity import ManagedEntity
from CricketDevice import CricketDevice
from CricketView import CricketView

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from DateTime import DateTime
from App.Dialogs import MessageDialog

from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from Products.ZenUtils.Utils import zenpathsplit, zenpathjoin

from ZenStatus import ZenStatus
from ZenDate import ZenDate
from Exceptions import *


def manage_createDevice(context, deviceName, devicePath="", 
            tag="", serialNumber="",
            snmpCommunity="", snmpPort=None,
            rackSlot=0, productionState=1000, comments="",
            manufacturer="", model="", 
            locationPath="", rack="",
            groupPaths=[], systemPaths=[],
            statusMonitors=["localhost"], cricketMonitor="localhost",
            REQUEST = None):

    "Device factory creates a device and sets up its relations"        

    if context.getDmdRoot("Devices").findDevice(deviceName):
        raise DeviceExistsError, "Device %s already exists" % deviceName
    if not devicePath:
        devicePath = "/Devices/Unknown"
        loginInfo = {}
        loginInfo['snmpCommunity'] = snmpCommunity
        loginInfo['snmpPort'] = snmpPort
        cEntry = context.getDmdRoot("Devices").ZenClassifier.classifyDevice(
                                    deviceName, loginInfo)
        if cEntry:
            devicePath = cEntry.getDeviceClassPath
            manufacturer = manufacturer and manufacturer \
                           or cEntry.getManufacturer
            model = model and model or cEntry.getProduct
        else:
            raise ZentinelException("Unable to classify device %s", deviceName)
    deviceClass = context.getDmdRoot("Devices").createOrganizer(devicePath)
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


def manage_addDevice(context, id, REQUEST = None):
    """make a device"""
    serv = Device(id)
    context._setObject(serv.id, serv)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main') 
                                     

addDevice = DTMLFile('dtml/addDevice',globals())

    
class Device(ZenModelRM, ManagedEntity, DeviceResultInt, 
             CricketView, CricketDevice):
    """
    Device is a key class within zenmon.  It represents the combination of
    compute hardware running an operating system.
    """

    event_key = portal_type = meta_type = 'Device'
    
    default_catalog = "deviceSearch" #device ZCatalog

    relationshipManagerPathRestriction = '/Devices'

    _properties = (
        {'id':'productionState', 'type':'keyedselection', 'mode':'w', 
           'select_variable':'getProdStateConversions','setter':'setProdState'},
        {'id':'tag', 'type':'string', 'mode':'w'},
        {'id':'serialNumber', 'type':'string', 'mode':'w'},
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

    _relations = (
        ("arptable", ToManyCont(ToOne, "ArpEntry", "device")),
        ("clientofservices", ToMany(ToMany, "IpService", "clients")),
        ("deviceClass", ToOne(ToManyCont, "DeviceClass", "devices")),
        ("groups", ToMany(ToMany, "DeviceGroup", "devices")),
        ("interfaces", ToManyCont(ToOne, "IpInterface", "device")),
        ("ipservices", ToManyCont(ToOne, "IpService", "server")),
        ("location", ToOne(ToMany, "Location", "devices")),
        ("model", ToOne(ToMany, "Hardware", "devices")),
        ("software", ToMany(ToMany, "Software", "copies")),
        ("monitors", ToMany(ToMany, "StatusMonitorConf", "devices")),
        ("cricket", ToOne(ToMany, "CricketConf", "devices")),
        ("routes", ToManyCont(ToOne, "IpRouteEntry", "device")),
        ("systems", ToMany(ToMany, "System", "devices")),
        ("termserver", ToOne(ToMany, "TerminalServer", "devices")),
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
            'immediate_view' : 'viewDeviceStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewDeviceStatus'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'detail'
                , 'name'          : 'Detail'
                , 'action'        : 'viewDeviceDetail'
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
                { 'id'            : 'performance'
                , 'name'          : 'Performance'
                , 'action'        : 'viewDevicePerformance'
                , 'permissions'   : (
                  permissions.view, )
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
                { 'id'            : 'config'
                , 'name'          : 'zProperties'
                , 'action'        : 'viewDeviceClassConfig'
                , 'permissions'   : ("Change Device",)
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

    security = ClassSecurityInfo()
    
    def __init__(self, id):
        ZenModelRM.__init__(self, id)
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
        self._lastPollSnmpUpTime = ZenStatus(0)
        self.snmpContact = ""
        self.snmpSysName = ""
        self.snmpLocation = ""
        self.osVersion = ""
        self.sshVersion = ""
        self.rackSlot = 0
        self.comments = ""
        self.snmpPort = 161
        self._snmpLastCollection = ZenDate('1968/1/8')
        self._lastChange = ZenDate('1968/1/8')
        self._lastCricketGenerate = ZenDate('1968/1/8')
        self.cpuType = ""
        self.totalMemory = 0.0
        self._cricketTargetMap = {}
        self._cricketTargetPath = ''

    
    def __getattr__(self, name):
        if name == 'datacenter':
            return self.getDataCenter()
        elif name == 'snmpUpTime':
            return self._snmpUpTime.getStatus()
        elif name == 'lastPollSnmpUpTime':
            return self._lastPollSnmpUpTime.getStatus()
        elif name == 'snmpLastCollection':
            return self._snmpLastCollection.getDate()
        else:
            raise AttributeError, name


    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'snmpLastCollection':
            self.setSnmpLastCollection(value)
        else:    
            setattr(self,id,value)


    security.declareProtected('View', 'getLocationName')
    def getLocationName(self):
        """return the full location name ie /Location/SubLocation/Rack"""
        loc = self.location()
        if loc: return loc.getOrganizerName()
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
        return map(lambda x: x.getOrganizerName(), self.systems())


    security.declareProtected('View', 'getDeviceGroupNames')
    def getDeviceGroupNames(self):
        """get the device group names for this device"""
        return map(lambda x: x.getOrganizerName(), self.groups())


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


    security.declareProtected('View', 'getLastChange')
    def getLastChange(self):
        return self._lastChange.getDate()

    
    security.declareProtected('View', 'getLastChangeString')
    def getLastChangeString(self):
        return self._lastChange.getString()


    security.declareProtected('View', 'getLastChange')
    def getLastCricketGenerate(self):
        return self._lastCricketGenerate.getDate()

    
    security.declareProtected('View', 'getLastChangeString')
    def getLastCricketGenerateString(self):
        return self._lastCricketGenerate.getString()


    security.declareProtected('View', 'getSnmpLastCollection')
    def getSnmpLastCollection(self):
        return self._snmpLastCollection.getDate()

    
    security.declareProtected('View', 'getSnmpLastCollectionString')
    def getSnmpLastCollectionString(self):
        return self._snmpLastCollection.getString()


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
    def getDeviceInterfaceIndexDict(self):
        """
        Build a dictionary of interfaces keyed on ifindex
        Used by SnmpCollector.CustomMaps.RouteMap to connect routes
        with interfaces.
        """
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
        dclass = self.getDmdRoot("Devices")
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
            logging.info("setting manufacturer to %s model to %s"
                            % (manufacturer, model))
            self.setModel(manufacturer, model)

        if locationPath: 
            if rack:
                locationPath += "/%s" % rack
                logging.info("setting rack location to %s" % locationPath)
                self.setRackLocation(locationPath)
            else:
                logging.info("setting location to %s" % locationPath)
                self.setLocation(locationPath)

        if groupPaths: 
            logging.info("setting group %s" % groupPaths)
            self.setGroups(groupPaths)

        if systemPaths: 
            logging.info("setting system %s" % systemPaths)
            self.setSystems(systemPaths)

        logging.info("setting status monitor to %s" % statusMonitors)
        self.setStatusMonitors(statusMonitors)

        logging.info("setting cricket monitor to %s" % cricketMonitor)
        self.setCricketMonitor(cricketMonitor)
       
        self.setLastChange()
        if REQUEST: 
            REQUEST['message'] = "Device Saved at time:"
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setProdState')
    def setProdState(self, state):
        self.productionState = int(state)


    security.declareProtected('Change Device', 'setLastChange')
    def setLastChange(self, value=None):
        self._lastChange.setDate(value)


    security.declareProtected('Change Device', 'setLastCricketGenerate')
    def setLastCricketGenerate(self, value=None):
        self._lastCricketGenerate.setDate(value)


    security.declareProtected('Change Device', 'setSnmpLastCollection')
    def setSnmpLastCollection(self, value=None):
        self._snmpLastCollection.setDate(value)


    security.declareProtected('Change Device', 'addManufacturer')
    def addManufacturer(self, newManufacturerName, REQUEST=None):
        """add a manufacturer to the database"""
        self.getDmdRoot("Companies").getCompany(newManufacturerName)
        if REQUEST:
            REQUEST['manufacturer'] = newManufacturerName
            REQUEST['message'] = ("Added Manufacturer %s at time:" 
                                    % newManufacturerName)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setModel')
    def setModel(self, manufacturer, model, newModelName="", REQUEST=None):
        """set the model of this device"""
        if newModelName: model = newModelName
        modelObj = self.getDmdRoot("Products").getModelProduct(
                                        manufacturer, model)
        self.addRelation("model", modelObj)
        if REQUEST:
            REQUEST['message'] = ("Set Manufacturer %s and Model %s at time:" 
                                    % (manufacturer, model))
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setLocation')
    def setLocation(self, locationPath, REQUEST=None):
        """set the location of a device within a generic location path"""
        locobj = self.getDmdRoot("Locations").createOrganizer(locationPath)
        self.addRelation("location", locobj)


    def addLocation(self, newLocationPath, REQUEST=None):
        """Add a new location and relate it to this device"""
        locobj = self.getDmdRoot("Locations").createOrganizer(newLocationPath)
        if REQUEST:
            REQUEST['locationPath'] = newLocationPath
            REQUEST['message'] = "Added Location %s at time:" % newLocationPath
            return self.callZenScreen(REQUEST)
   

    security.declareProtected('Change Device', 'setCricketMonitor')
    def setCricketMonitor(self, cricketMonitor,
                            newCricketMonitor=None, REQUEST=None):
        """set the cricket monitor for this device if newCricketMonitor
        is passed in create it"""
        if newCricketMonitor: cricketMonitor = newCricketMonitor
        obj = self.getDmdRoot("Monitors").getCricketMonitor(
                                                    cricketMonitor)
        self.addRelation("cricket", obj)
        if REQUEST:
            REQUEST['message'] = "Set Cricket %s at time:" % cricketMonitor
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setStatusMonitors')
    def setStatusMonitors(self, statusMonitors):
        objGetter = self.getDmdRoot("Monitors").getStatusMonitor
        self._setRelations("monitors", objGetter, statusMonitors)


    security.declareProtected('Change Device', 'addStatusMonitor')
    def addStatusMonitor(self, newStatusMonitor, REQUEST=None):
        """add new status monitor to the database and this device"""
        mon = self.getDmdRoot("Monitors").getStatusMonitor(newStatusMonitor)
        self.addRelation("monitors", mon)
        if REQUEST:
            REQUEST['message'] = "Added Monitor %s at time:" % newStatusMonitor
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setGroups')
    def setGroups(self, groupPaths):
        """set the list of groups for this device based on a list of paths"""
        objGetter = self.getDmdRoot("Groups").createOrganizer
        self._setRelations("groups", objGetter, groupPaths)


    security.declareProtected('Change Device', 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """add a device group to the database and this device"""
        group = self.getDmdRoot("Groups").createOrganizer(newDeviceGroupPath)
        self.addRelation("groups", group)
        if REQUEST:
            REQUEST['message'] = "Added Group %s at time:" % newDeviceGroupPath
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setSystems')
    def setSystems(self, systemPaths):
        """set a list of systems to this device using their system paths"""
        objGetter = self.getDmdRoot("Systems").createOrganizer
        self._setRelations("systems", objGetter, systemPaths)
      

    security.declareProtected('Change Device', 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """add a systems to this device using its system path"""
        sys = self.getDmdRoot("Systems").createOrganizer(newSystemPath)
        self.addRelation("systems", sys)
        if REQUEST:

            return self.callZenScreen(REQUEST)


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
            curRelIds[value.getOrganizerName()] = value
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


    def getSnmpStatusNumber(self):
        '''get a device's raw snmp status number'''
        return self.getStatus('SnmpStatus')


    security.declareProtected('View', 'getSnmpStatus')
    def getSnmpStatus(self):
        '''get a device's snmp status and perform conversion'''
        return self.getStatusString('SnmpStatus')


    def pastSnmpMaxFailures(self):
        """Device has more SNMP failures than maxFailures on its status mon."""
        statusmon = self.monitors()
        if len(statusmon) > 0: 
            statusmon = statusmon[0]
            return statusmon.maxFailures < self.getSnmpStatusNumber()
        return False


    def _getDeviceName(self):
        '''Return the device name id'''
        return self.getId()


    def _getDeviceClassPath(self):
        """Return the device class path in the form /Server/Linux"""
        return self.deviceClass().getOrganizerName()

    getDeviceClassName = _getDeviceClassPath


    def _getProdState(self):
        '''Return the production state of the device'''
        return self.convertProdState(self.productionState)

    
    ####################################################################
    # Status Management Functions used by status monitors
    ####################################################################


    security.declareProtected('Manage Device Status', 'setSnmpUpTime')
    def setSnmpUpTime(self, value):
        """set the value of the snmpUpTime status object"""
        self._snmpUpTime.setStatus(value)


    security.declareProtected('Manage Device Status', 'setSnmpUpTime')
    def getLastPollSnmpUpTime(self):
        """set the value of the snmpUpTime status object"""
        return self._lastPollSnmpUpTime.getStatus()


    security.declareProtected('Manage Device Status', 'setSnmpUpTime')
    def setLastPollSnmpUpTime(self, value):
        """set the value of the snmpUpTime status object"""
        self._lastPollSnmpUpTime.setStatus(value)


    def snmpAgeCheck(self, hours):
        lastcoll = self.getSnmpLastCollection()
        hours = hours/24.0
        if DateTime() > lastcoll + hours: return 1


    ####################################################################
    # Management Functions
    ####################################################################

    security.declareProtected('Change Device', 'collectConfig')
    def collectConfig(self, REQUEST=None):
        """collect the configuration of this device"""
        from Products.SnmpCollector.SnmpCollector import SnmpCollector
        sc = SnmpCollector(noopts=1,app=self.getPhysicalRoot())
        sc.options.force = True
        if REQUEST:
            response = REQUEST.RESPONSE
            sc.setLoggingStream(response)
        try:
            sc.collectDevice(self)
        except:
            logging.exception('exception while collecting snmp for device %s'
                              %  self.getId())
        else:
            logging.info('collected snmp information for device %s'
                            % self.getId())



    security.declareProtected('Change Device', 'deleteDevice')
    def deleteDevice(self, REQUEST=None):
        """Delete device from the DMD"""
        parent = self.getPrimaryParent()
        parent._delObject(self.getId())
        if REQUEST:
            REQUEST['RESPONSE'].redirect(parent.absolute_url() + 
                                            "/deviceOrganizerStatus")


    security.declareProtected('Change Device', 'renameDevice')
    def renameDevice(self, newId, REQUEST=None):
        """Delete device from the DMD"""
        parent = self.getPrimaryParent()
        parent.manage_renameObject(self.getId(), newId)
        self.setLastChange()
        if REQUEST: return self()


    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        if item == self: 
            self.index_object()
            ZenModelRM.manage_afterAdd(self, item, container)


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        ZenModelRM.manage_afterClone(self, item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        if item == self or getattr(item, "_operation", -1) < 1: 
            ZenModelRM.manage_beforeDelete(self, item, container)
            self.unindex_object()


    def index_object(self):
        """A common method to allow Findables to index themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.catalog_object(self, self.getId())
            
                                                
    def unindex_object(self):
        """A common method to allow Findables to unindex themselves."""
        cat = getattr(self, self.default_catalog, None)
        if cat != None: 
            cat.uncatalog_object(self.getId())


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
