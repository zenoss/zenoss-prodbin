#################################################################
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

import sys
import time
import socket
import logging
log = logging.getLogger("zen.Device")

from Products.ZenUtils.Utils import setWebLoggingStream, clearWebLoggingStream

# base classes for device
from ManagedEntity import ManagedEntity
from PingStatusInt import PingStatusInt
from CricketDevice import CricketDevice

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base
from DateTime import DateTime
from App.Dialogs import MessageDialog

from AccessControl import Permissions as permissions

from Products.SnmpCollector.SnmpCollector import findSnmpCommunity
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.IpUtil import isip
from Products.ZenEvents.ZenEventClasses import SnmpStatus

from OperatingSystem import OperatingSystem
from DeviceHW import DeviceHW

from ZenStatus import ZenStatus
from ZenDate import ZenDate
from Exceptions import *


def manage_createDevice(context, deviceName, devicePath="", 
            tag="", serialNumber="",
            zSnmpCommunity="", zSnmpPort=161, zSnmpVer="v1",
            rackSlot=0, productionState=1000, comments="",
            hwManufacturer="", hwProductName="", 
            osManufacturer="", osProductName="", 
            locationPath="", groupPaths=[], systemPaths=[],
            statusMonitors=["localhost"], cricketMonitor="localhost",
            REQUEST = None):

    "Device factory creates a device and sets up its relations"        

    if context.getDmdRoot("Devices").findDevice(deviceName):
        raise DeviceExistsError, "Device %s already exists" % deviceName
    if not devicePath: devicePath = "/Discovered"
    deviceClass = context.getDmdRoot("Devices").createOrganizer(devicePath)
    device = deviceClass.createInstance(deviceName)
    if not zSnmpCommunity:
        zSnmpCommunity = findSnmpCommunity(deviceClass, deviceName)
    device.manage_editDevice(
                tag, serialNumber,
                zSnmpCommunity, zSnmpPort, zSnmpVer,
                rackSlot, productionState, comments,
                hwManufacturer, hwProductName, 
                osManufacturer, osProductName, 
                locationPath, groupPaths, systemPaths,
                statusMonitors, cricketMonitor)
                
    return device


def manage_addDevice(context, id, REQUEST = None):
    """make a device"""
    serv = Device(id)
    context._setObject(serv.id, serv)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main') 
                                     

addDevice = DTMLFile('dtml/addDevice',globals())

    
class Device(PingStatusInt, CricketDevice, ManagedEntity):
    """
    Device is a key class within zenmon.  It represents the combination of
    compute hardware running an operating system.
    """

    event_key = portal_type = meta_type = 'Device'
    
    default_catalog = "deviceSearch" #device ZCatalog

    relationshipManagerPathRestriction = '/Devices'

    productionState = 1000
    snmpAgent = ""
    snmpDescr = ""
    snmpOid = ""
    snmpContact = ""
    snmpSysName = ""
    snmpLocation = ""
    rackSlot = 0
    comments = ""
    sysedgeLicenseMode = ""

    _properties = ManagedEntity._properties + (
        {'id':'productionState', 'type':'keyedselection', 'mode':'w', 
           'select_variable':'getProdStateConversions','setter':'setProdState'},
        {'id':'snmpAgent', 'type':'string', 'mode':'w'},
        {'id':'snmpDescr', 'type':'string', 'mode':''},
        {'id':'snmpOid', 'type':'string', 'mode':''},
        {'id':'snmpUpTime', 'type':'int', 'mode':''},
        {'id':'snmpContact', 'type':'string', 'mode':''},
        {'id':'snmpSysName', 'type':'string', 'mode':''},
        {'id':'snmpLocation', 'type':'string', 'mode':''},
        {'id':'snmpLastCollection', 'type':'date', 'mode':''},
        {'id':'snmpAgent', 'type':'string', 'mode':''},
        {'id':'rackSlot', 'type':'int', 'mode':'w'},
        {'id':'comments', 'type':'text', 'mode':'w'},
        {'id':'sysedgeLicenseMode', 'type':'string', 'mode':''},
        ) 


    _relations = ManagedEntity._relations + (
        ("deviceClass", ToOne(ToManyCont, "DeviceClass", "devices")),
        ("termserver", ToOne(ToMany, "TerminalServer", "devices")),
        ("monitors", ToMany(ToMany, "StatusMonitorConf", "devices")),
        ("cricket", ToOne(ToMany, "CricketConf", "devices")),
        ("location", ToOne(ToMany, "Location", "devices")),
        ("systems", ToMany(ToMany, "System", "devices")),
        ("groups", ToMany(ToMany, "DeviceGroup", "devices")),
        #("dhcpubrclients", ToMany(ToMany, "UBRRouter", "dhcpservers")),
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
            'immediate_view' : 'deviceStatus',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'deviceStatus'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'osdetail'
                , 'name'          : 'OS Detail'
                , 'action'        : 'deviceOsDetail'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'hwdetail'
                , 'name'          : 'Hardware'
                , 'action'        : 'deviceHardwareDetail'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'swdetail'
                , 'name'          : 'Software'
                , 'action'        : 'deviceSoftwareDetail'
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
                , 'action'        : 'zPropertyEdit'
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
        ManagedEntity.__init__(self, id)
        os = OperatingSystem()
        self._setObject(os.id, os)
        hw = DeviceHW()
        self._setObject(hw.id, hw)
        #self.commandStatus = "Not Tested"
        self._snmpUpTime = ZenStatus(-1)
        self._lastPollSnmpUpTime = ZenStatus(0)
        self._snmpLastCollection = ZenDate('1968/1/8')
        self._lastChange = ZenDate('1968/1/8')
        self._lastCricketGenerate = ZenDate('1968/1/8')

    
    def __getattr__(self, name):
        if name == 'snmpUpTime':
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
            ManagedEntity._setPropValue(self, id, value)


    def traceRoute(self, target, ippath=None):
        if ippath is None: ippath=[]
        if not isip(target): target = socket.gethostbyname(target)
        return self.os.traceRoute(target, ippath)


    def getHWProductKey(self):
        """Get our HW product by productKey.
        """
        return self.hw.getProductKey()


    def getOSProductKey(self):
        """Get our OS product by productKey.
        """
        return self.os.getProductKey()


    def setOSProductKey(self, prodKey):
        """Set our OS product by productKey.
        """
        self.os.setProductKey(prodKey)


    def setHWProductKey(self, prodKey):
        """Set our HW product by productKey.
        """
        self.hw.setProductKey(prodKey)


    def followNextHopIps(self):
        """Return the ips that our indirect routs point to which 
        aren't currently connected to devices.
        """
        ips = []
        for r in self.os.routes():
            ipobj = r.nexthop()
            #if ipobj and not ipobj.device(): 
            if ipobj: ips.append(ipobj.id)
        return ips


    security.declareProtected('View', 'getLocationName')
    def getLocationName(self):
        """return the full location name ie /Location/SubLocation/Rack"""
        loc = self.location()
        if loc: return loc.getOrganizerName()
        return ""


    def getLocationLink(self):
        """Return an a link to the devices location.
        """
        loc = self.location()
        if loc: return "<a href='%s'>%s</a>" % (loc.getPrimaryUrlPath(),
                                                loc.getOrganizerName())
        return ""


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
        return self.os.version()


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


    security.declareProtected('View', 'getManageIp')
    def getManageIp(self):
        """Return the management ip for this device. See getManageInterface.
        """
        int = self.os.getManageInterface()
        if int: return int.getIp()
        return ""

    
    security.declareProtected('View', 'getManageInterface')
    def getManageInterface(self):
        """Return the management interface of a device looks first
        for zManageInterfaceNames in aquisition path if not found
        uses default 'Loopback0' and 'Ethernet0' if none of these are found
        returns the first interface if there is any.
        """
        return self.os.getManageInterface()

    
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
                zSnmpCommunity="", zSnmpPort=161, zSnmpVer="v1",
                rackSlot=0, productionState=1000, comments="",
                hwManufacturer="", hwProductName="", 
                osManufacturer="", osProductName="", 
                locationPath="", groupPaths=[], systemPaths=[],
                statusMonitors=["localhost"], cricketMonitor="localhost",
                REQUEST=None):
        """edit device relations and attributes"""
        self.tag = tag
        self.serialNumber = serialNumber
        if self.zSnmpCommunity != zSnmpCommunity:
            self.setZenProperty("zSnmpCommunity", zSnmpCommunity)
        if self.zSnmpPort != zSnmpPort:
            self.setZenProperty("zSnmpPort", zSnmpPort)
        if self.zSnmpVer != zSnmpVer:
            self.setZenProperty("zSnmpVer", zSnmpVer)

        self.rackSlot = rackSlot
        self.productionState = productionState
        self.comments = comments

        if hwManufacturer and hwProductName:
            log.info("setting hardware manufacturer to %s productName to %s"
                            % (hwManufacturer, hwProductName))
            self.hw.setProduct(hwProductName, hwManufacturer)

        if osManufacturer and osProductName:
            log.info("setting os manufacturer to %s productName to %s"
                            % (osManufacturer, osProductName))
            self.os.setProduct(osProductName, osManufacturer)

        if locationPath: 
            log.info("setting location to %s" % locationPath)
            self.setLocation(locationPath)

        if groupPaths: 
            log.info("setting group %s" % groupPaths)
            self.setGroups(groupPaths)

        if systemPaths: 
            log.info("setting system %s" % systemPaths)
            self.setSystems(systemPaths)

        log.info("setting status monitor to %s" % statusMonitors)
        self.setStatusMonitors(statusMonitors)

        log.info("setting cricket monitor to %s" % cricketMonitor)
        self.setCricketMonitor(cricketMonitor)
       
        self.setLastChange()
        if REQUEST: 
            REQUEST['message'] = "Device Saved at time:"
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setProdState')
    def setProdState(self, state):
        """Set a device's production state as an integer.
        """
        self.productionState = int(state)


    security.declareProtected('Change Device', 'setLastChange')
    def setLastChange(self, value=None):
        """Set the changed datetime for this device. value default is now.
        """
        self._lastChange.setDate(value)


    security.declareProtected('Change Device', 'setLastCricketGenerate')
    def setLastCricketGenerate(self, value=None):
        """Set the last time cricket generation occurred. value default is now.
        """
        self._lastCricketGenerate.setDate(value)


    security.declareProtected('Change Device', 'setSnmpLastCollection')
    def setSnmpLastCollection(self, value=None):
        """Set the last time snmp collection occurred. value default is now.
        """
        self._snmpLastCollection.setDate(value)


    security.declareProtected('Change Device', 'addManufacturer')
    def addManufacturer(self, newHWManufacturerName=None, 
                        newSWManufacturerName=None, REQUEST=None):
        """Add a manufacturer to the database"""
        mname = newHWManufacturerName
        field = 'hwManufacturer'
        if not mname: 
            mname = newSWManufacturerName
            field = 'osManufacturer'
        self.getDmdRoot("Manufacturers").createManufacturer(mname)
        if REQUEST:
            REQUEST[field] = mname
            REQUEST['message'] = ("Added Manufacturer %s at time:" % mname)
            return self.callZenScreen(REQUEST)




    security.declareProtected('Change Device', 'setHWProduct')
    def setHWProduct(self, newHWProductName, hwManufacturer, REQUEST=None):
        """set the productName of this device"""
        self.getDmdRoot("Manufacturers").createHardwareProduct(
                                        newHWProductName, hwManufacturer)
        if REQUEST:
            REQUEST['hwProductName'] = newHWProductName
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setOSProduct')
    def setOSProduct(self, newOSProductName, osManufacturer, REQUEST=None):
        """set the productName of this device"""
        self.getDmdRoot("Manufacturers").createSoftwareProduct(
                                        newOSProductName, osManufacturer)
        if REQUEST:
            REQUEST['osProductName'] = newOSProductName
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

    security.declareProtected('View', 'device')
    def device(self):
        """support DeviceResultInt mixin class"""
        return self


    security.declareProtected('View', 'getSnmpStatus')
    def getSnmpStatus(self):
        '''get a device's snmp status and perform conversion'''
        if getattr(self, 'zSnmpMonitorIgnore', False):
            status = -1
        else:
            status = self.getStatus(SnmpStatus)
        return status
    getSnmpStatusNumber = getSnmpStatus


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
    def collectConfig(self, setlog=True, REQUEST=None):
        """collect the configuration of this device"""
        if REQUEST and setlog:
            response = REQUEST.RESPONSE
            dlh = self.deviceLoggingHeader()
            idx = dlh.rindex("</table>")
            response.write(dlh[:idx])
            handler = setWebLoggingStream(response)
        try:
            from Products.DataCollector.zenmodeler import ZenModeler
            sc = ZenModeler(noopts=1,app=self.getPhysicalRoot(),single=True)
            sc.options.force = True
            sc.collectDevice(self)
        except:
            log.exception('exception collecting data for device %s',self.id)
            sc.stop()
        else:
            log.info('collected snmp information for device %s',self.id)
                            
        if REQUEST and setlog:
            response.write(self.deviceLoggingFooter())
            clearWebLoggingStream(handler)



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
            ManagedEntity.manage_afterAdd(self, item, container)


    def manage_afterClone(self, item):
        """Not really sure when this is called."""
        ManagedEntity.manage_afterClone(self, item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        if item == self or getattr(item, "_operation", -1) < 1: 
            ManagedEntity.manage_beforeDelete(self, item, container)
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


InitializeClass(Device)
