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

import time
import types
import socket
import logging
log = logging.getLogger("zen.Device")

from _mysql_exceptions import OperationalError

from urllib import quote as urlquote

from Products.ZenUtils.Graphics import NetworkGraph
from Products.ZenUtils.Utils import isXmlRpc, setupLoggingHeader, executeCommand
from Products.ZenUtils.Utils import zenPath, unused, clearWebLoggingStream
from Products.ZenUtils import Time
import RRDView
from Products.ZenUtils.IpUtil import checkip, IpAddressError, maskToBits

# base classes for device
from ManagedEntity import ManagedEntity

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import InitializeClass
from DateTime import DateTime

from ZODB.POSException import POSError

#from Products.SnmpCollector.SnmpCollector import findSnmpCommunity
from Products.DataCollector.ApplyDataMap import ApplyDataMap

from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.IpUtil import isip
from Commandable import Commandable
from Lockable import Lockable
from MaintenanceWindowable import MaintenanceWindowable
from AdministrativeRoleable import AdministrativeRoleable
from ZenMenuable import ZenMenuable

from OperatingSystem import OperatingSystem
from DeviceHW import DeviceHW

from ZenStatus import ZenStatus
from Products.ZenModel.Exceptions import *
from ZenossSecurity import *
from Products.ZenUtils.Utils import edgesToXML
from Products.ZenUtils import NetworkTree

def manage_createDevice(context, deviceName, devicePath="/Discovered",
            tag="", serialNumber="",
            zSnmpCommunity="", zSnmpPort=161, zSnmpVer="",
            rackSlot=0, productionState=1000, comments="",
            hwManufacturer="", hwProductName="",
            osManufacturer="", osProductName="",
            locationPath="", groupPaths=[], systemPaths=[],
            performanceMonitor="localhost",
            discoverProto="snmp", priority=3, manageIp=None):
    """
    Device factory creates a device and sets up its relations and collects its
    configuration. SNMP Community discovery also happens here. If an IP is
    passed for deviceName it will be used for collection and the device name
    will be set to the SNMP SysName (or ptr if SNMP Fails and ptr is valid)
    
    @rtype: Device
    """
    ip = None
    if isip(deviceName):
        ip = deviceName
        deviceName = ""
    if manageIp and isip(manageIp):
        ip = manageIp
    if ip:
        ipobj = context.getDmdRoot('Networks').findIp(ip)
        if ipobj:
            dev = ipobj.device()
            if dev:
                raise DeviceExistsError("Ip %s exists on %s" % (ip, dev.id))
    else:
        deviceName = context.prepId(deviceName)
        try: ip = socket.gethostbyname(deviceName)
        except socket.error: ip = ""
        if context.getDmdRoot("Devices").findDevice(deviceName):
            raise DeviceExistsError("Device %s already exists" % deviceName)
    if not ip:
        raise NoIPAddress("No IP found for name %s" % deviceName)
    if discoverProto == "snmp":
        zSnmpCommunity, zSnmpPort, zSnmpVer, snmpname = \
                        findCommunity(context, ip, devicePath,
                                      zSnmpCommunity, zSnmpPort, zSnmpVer)
        log.debug("device community = %s", zSnmpCommunity)
        log.debug("device version = %s", zSnmpVer)
        log.debug("device name = %s", snmpname)
        if not deviceName:
            # use the ptr record we already have
            try:
                ptrName = ''
                if ipobj and ipobj.ptrName:
                    ptrName = ipobj.ptrName
                if ptrName and socket.gethostbyname(ptrName):
                    deviceName = ptrName
            except socket.error: pass
            
            # lookup the ptr record
            try:
                if not deviceName and ip:
                    deviceName = socket.gethostbyaddr(ip)[0]
            except socket.error: pass

            # use the snmpname
            if not deviceName and snmpname:
                deviceName = snmpname
                
            # give up: use ip
            if not deviceName:
                log.warn("unable to name device using ip '%s'", ip)
                deviceName = ip
    elif discoverProto == "command":
        raise ZenModelError("discover protocol 'ssh' not implemented yet")
    if not deviceName:
        deviceName = ip
    log.info("device name '%s' for ip '%s'", deviceName, ip)
    deviceClass = context.getDmdRoot("Devices").createOrganizer(devicePath)
    deviceName = context.prepId(deviceName)
    device = deviceClass.createInstance(deviceName)
    device.setManageIp(ip)
    device.manage_editDevice(
                tag, serialNumber,
                zSnmpCommunity, zSnmpPort, zSnmpVer,
                rackSlot, productionState, comments,
                hwManufacturer, hwProductName,
                osManufacturer, osProductName,
                locationPath, groupPaths, systemPaths,
                performanceMonitor, priority)
# Not sure why this was important but it causes issues if
# we are adding an alias to an existing box.  It will take
# away that boxes IP.  It also seems to make a network with
# the wrong netmask.
#    if discoverProto == "none":
#        from Products.ZenModel.IpInterface import IpInterface
#        tmpInterface = IpInterface('eth0')
#        device.os.interfaces._setObject('eth0', tmpInterface)
#        interface = device.getDeviceComponents()[0]
#        interface.addIpAddress(device.getManageIp())
    return device


def findCommunity(context, ip, devicePath, 
                  community="", port=None, version=None):
    """
    Find the SNMP community and version for an ip address using zSnmpCommunities.
    
    @rtype: tuple of (community, port, version, device name)
    """
    from pynetsnmp.SnmpSession import SnmpSession

    devroot = context.getDmdRoot('Devices').createOrganizer(devicePath)
    communities = []
    if community: communities.append(community)
    communities.extend(getattr(devroot, "zSnmpCommunities", []))
    if not port: port = getattr(devroot, "zSnmpPort", 161)
    versions = ('v2c', 'v1')
    if not version: version = getattr(devroot, 'zSnmpVer', None)
    if version: versions = (version,)
    timeout = getattr(devroot, "zSnmpTimeout", 2)
    retries = getattr(devroot, "zSnmpTries", 2)
    session = SnmpSession(ip, timeout=timeout, port=port, retries=retries)
    oid = '.1.3.6.1.2.1.1.5.0'
    goodcommunity = ""
    goodversion = ""
    devname = ""
    for version in versions:
        session.setVersion(version)
        for community in communities:
            session.community = community
            try:
                devname = session.get(oid).values()[0]
                goodcommunity = session.community
                goodversion = version
                break
            except (SystemExit, KeyboardInterrupt, POSError): raise
            except: pass #keep trying until we run out
        if goodcommunity:
	        break
    else:
        raise NoSnmp("no snmp found for ip = %s" % ip)
    return (goodcommunity, port, goodversion, devname)

def manage_addDevice(context, id, REQUEST = None):
    """
    Creates a device
    """
    serv = Device(id)
    context._setObject(serv.id, serv)
    if REQUEST is not None:
        REQUEST['message'] = "Device created"
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addDevice = DTMLFile('dtml/addDevice',globals())


class Device(ManagedEntity, Commandable, Lockable, MaintenanceWindowable,
            AdministrativeRoleable, ZenMenuable):
    """
    Device is a base class that represents the idea of a single computer system
    that is made up of software running on hardware. It currently must be IP
    enabled but maybe this will change.
    """

    event_key = portal_type = meta_type = 'Device'
    
    default_catalog = "deviceSearch" #device ZCatalog

    relationshipManagerPathRestriction = '/Devices'

    manageIp = ""
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
    priority = 3

    _properties = ManagedEntity._properties + (
        {'id':'manageIp', 'type':'string', 'mode':'w'},
        {'id':'productionState', 'type':'keyedselection', 'mode':'w',
           'select_variable':'getProdStateConversions','setter':'setProdState'},
        {'id':'snmpAgent', 'type':'string', 'mode':'w'},
        {'id':'snmpDescr', 'type':'string', 'mode':''},
        {'id':'snmpOid', 'type':'string', 'mode':''},
        {'id':'snmpContact', 'type':'string', 'mode':''},
        {'id':'snmpSysName', 'type':'string', 'mode':''},
        {'id':'snmpLocation', 'type':'string', 'mode':''},
        {'id':'snmpLastCollection', 'type':'date', 'mode':''},
        {'id':'snmpAgent', 'type':'string', 'mode':''},
        {'id':'rackSlot', 'type':'int', 'mode':'w'},
        {'id':'comments', 'type':'text', 'mode':'w'},
        {'id':'sysedgeLicenseMode', 'type':'string', 'mode':''},
        {'id':'priority', 'type':'int', 'mode':'w'},
        )

    _relations = ManagedEntity._relations + (
        ("deviceClass", ToOne(ToManyCont, "Products.ZenModel.DeviceClass", 
            "devices")),
        ("perfServer", ToOne(ToMany, "Products.ZenModel.PerformanceConf", 
            "devices")),
        ("location", ToOne(ToMany, "Products.ZenModel.Location", "devices")),
        ("systems", ToMany(ToMany, "Products.ZenModel.System", "devices")),
        ("groups", ToMany(ToMany, "Products.ZenModel.DeviceGroup", "devices")),
        ("maintenanceWindows",ToManyCont(ToOne, 
            "Products.ZenModel.MaintenanceWindow", "productionState")),
        ("adminRoles", ToManyCont(ToOne,"Products.ZenModel.AdministrativeRole",
            "managedObject")),
        ('userCommands', ToManyCont(ToOne, 'Products.ZenModel.UserCommand', 
            'commandable')),
        # unused:
        ('monitors', ToMany(ToMany, 'Products.ZenModel.StatusMonitorConf',
            'devices')),
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
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'osdetail'
                , 'name'          : 'OS'
                , 'action'        : 'deviceOsDetail'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'hwdetail'
                , 'name'          : 'Hardware'
                , 'action'        : 'deviceHardwareDetail'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'swdetail'
                , 'name'          : 'Software'
                , 'action'        : 'deviceSoftwareDetail'
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
                { 'id'            : 'perfServer'
                , 'name'          : 'Perf'
                , 'action'        : 'viewDevicePerformance'
                , 'permissions'   : (ZEN_VIEW, )
                },
#                { 'id'            : 'perfConf'
#                , 'name'          : 'PerfConf'
#                , 'action'        : 'objTemplates'
#                , 'permissions'   : ("Change Device", )
#                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editDevice'
                , 'permissions'   : ("Change Device",)
                },
#                { 'id'            : 'management'
#                , 'name'          : 'Administration'
#                , 'action'        : 'deviceManagement'
#                , 'permissions'   : ("Change Device",)
#                },
#                { 'id'            : 'custom'
#                , 'name'          : 'Custom'
#                , 'action'        : 'deviceCustomEdit'
#                , 'permissions'   : (ZEN_VIEW, )
#                },
#                { 'id'            : 'config'
#                , 'name'          : 'zProperties'
#                , 'action'        : 'zPropertyEdit'
#                , 'permissions'   : (ZEN_VIEW,)
#                },
#                { 'id'            : 'viewHistory'
#                , 'name'          : 'Modifications'
#                , 'action'        : 'viewHistory'
#                , 'permissions'   : (ZEN_VIEW, )
#                },
#                { 'id'            : 'zProperties'
#                , 'name'          : 'zProperties'
#                , 'action'        : 'zPropertyEdit'
#                , 'permissions'   : (  ZEN_VIEW, )
#                },
            )
         },
        )

    security = ClassSecurityInfo()
    
    def __init__(self, id, buildRelations=True):
        ManagedEntity.__init__(self, id, buildRelations=buildRelations)
        os = OperatingSystem()
        self._setObject(os.id, os)
        hw = DeviceHW()
        self._setObject(hw.id, hw)
        #self.commandStatus = "Not Tested"
        self._lastPollSnmpUpTime = ZenStatus(0)
        self._snmpLastCollection = 0
        self._lastChange = 0


    def getRRDTemplate(self):
        """
        DEPRECATED
        """
        import warnings
        warnings.warn('Device.getRRDTemplate is deprecated',
                         DeprecationWarning)
        return ManagedEntity.getRRDTemplate(self)

    def getRRDTemplates(self):
        """
        Returns all the templates bound to this Device
        
        @rtype: list

        >>> from Products.ZenModel.Device import manage_addDevice
        >>> manage_addDevice(devices, 'test')
        >>> devices.test.getRRDTemplates()
        [<RRDTemplate at /zport/dmd/Devices/rrdTemplates/Device>]
        """
        if not hasattr(self, 'zDeviceTemplates'):
            return ManagedEntity.getRRDTemplates(self)
        result = []
        for name in self.zDeviceTemplates:
            template = self.getRRDTemplateByName(name)
            if template:
                result.append(template)
        return result


    def getRRDNames(self):
        return ['sysUpTime']

        
    def getDataSourceOptions(self):
        """
        Returns the available DataSource options. DataSource options 
        are used to populate the dropdown when adding a new DataSource 
        and is a string.  See L{RRDTemplate.RRDTemplate.getDataSourceOptions} 
        for more information. 

        @rtype: list 
        @return: [(displayName, dsOption),]
        """ 
        # This is an unfortunate hack.  Called from the device templates
        # page where we show multiple templates now.  This only really
        # works because getDataSourceOptions() returns the same values
        # for every template.  Ideally we would be able to pass some sort
        # of context to the Add DataSource dialog that calls this method.
        templates = self.getRRDTemplates()
        if templates:
            return templates[0].getDataSourceOptions()
        return []

    # security.declareProtected('Manage DMD', 'manage_resequenceRRDGraphs')
    # def manage_resequenceRRDGraphs(self, templateId, seqmap=(), origseq=(), REQUEST=None):
    #     """Reorder the sequecne of the RRDGraphs.
    #     """
    #     template = self.getRRDTemplateByName(templateId)
    #     return template.manage_resequenceRRDGraphs(seqmap, origseq, REQUEST)
            

    def sysUpTime(self):
        """
        Returns the cached sysUpTime for this device
        
        @rtype: int
        """
        try:
            return self.cacheRRDValue('sysUpTime', -1)
        except Exception:
            log.exception("failed getting sysUpTime")
            return -1


    def availability(self, *args, **kw):
        """
        Returns the uptime of this device
        
        @rtype: string
        @todo: Performance enhancement: Should move import outside of method
        """
        from Products.ZenEvents import Availability
        results = Availability.query(self.dmd, device=self.id, *args, **kw)
        if results:
            return results[0]
        else:
            return None


    # FIXME: cleanup --force option #2660
    def __getattr__(self, name):
        """
        Override from object to handle lastPollSnmpUpTime and 
        snmpLastCollection
        
        @todo: Not sure this is needed, see getLastPollSnmpUpTime and 
        getSnmpLastCollection
        """
        if name == 'lastPollSnmpUpTime':
            return self._lastPollSnmpUpTime.getStatus()
        elif name == 'snmpLastCollection':
            return DateTime(self._snmpLastCollection)
        else:
            raise AttributeError, name


    def _setPropValue(self, id, value):
        """
        Override from PropertyManager to handle checks and ip creation
        
        @todo: Not sure this is needed, see setSnmpLastCollection
        """
        self._wrapperCheck(value)
        if id == 'snmpLastCollection':
            self._snmpLastCollection = float(value)
        else:
            ManagedEntity._setPropValue(self, id, value)

    
    def applyDataMap(self, datamap, relname="", compname="", modname=""):
        """
        Apply a datamap passed as a list of dicts through XML-RPC.
        """
        adm = ApplyDataMap()
        adm.applyDataMap(self, datamap, relname=relname,
                         compname=compname, modname=modname)

    
    def path(self):
        """
        Return a sequence of path tuples suitable for indexing by 
        a MultiPathIndex.
        """
        orgs = (
                self.systems() + 
                self.groups() + 
                [self.location()] + 
                [self.deviceClass()]
               )
        orgs = filter(None, orgs)
        paths = []
        for org in orgs:
            rel = org.primaryAq().devices
            try:
                orgself = rel._getOb(self.getPrimaryId())
            except AttributeError:
                # Device class wants an id, not a path
                orgself = rel._getOb(self.getId())
            paths.append(orgself.getPhysicalPath())
        return paths


    def traceRoute(self, target, ippath=None):
        """
        Trace the route to target using our routing table.
        Wrapper method of OperatingSystem.traceRoute
        
        @param target: Device name
        @type target: string
        @param ippath: IP addesses
        @type ippath: list
        @return: IP Addresses
        @rtype: list
        """
        if ippath is None: ippath=[]
        if type(target) in types.StringTypes:
            target = self.findDevice(target)
            if not target: raise ValueError("target %s not found in dmd",target)
        return self.os.traceRoute(target, ippath)

    
    def getMonitoredComponents(self, collector=None, type=None):
        """
        Return list of monitored DeviceComponents on this device.
        Wrapper method for getDeviceComponents
        """
        return self.getDeviceComponents(monitored=True, 
                                        collector=collector, type=type)

    security.declareProtected(ZEN_VIEW, 'getDeviceComponents')
    def getDeviceComponents(self, monitored=None, collector=None, type=None):
        """
        Return list of all DeviceComponents on this device.
        
        @type monitored: boolean
        @type collector: string
        @type type: string
        @permission: ZEN_VIEW
        @rtype: list
        """
        # The getParentDeviceName index was added in 2.2.  During migrates
        # this code could execute before the 2.2 migrate steps are run, so we
        # need to properly cope with this case.
        # See ticket #2787
        if not self.componentSearch._catalog.indexes.has_key('getParentDeviceName'):
            return self.getDeviceComponentsNoIndexGen()
            
        query = {
            'getParentDeviceName':self.id,
            }
        if collector is not None:
            query['getCollectors'] = collector
        if monitored is not None:
            query['monitored'] = monitored
        if type is not None:
            query['meta_type'] = type
        brains = self.componentSearch(query)
        return [c.getObject() for c in brains]


    def getDeviceComponentsNoIndexGen(self):
        """
        Return a list of all device components by walking relations.  This is
        much slower then the normal getDeviceComponents method which uses the
        component index.  It is used when rebuilding the device indexes.
        """
        from DeviceComponent import DeviceComponent
        for baseObject in (self, self.os, self.hw):
            for rel in baseObject.getRelationships():
                if rel.meta_type != "ToManyContRelationship": continue
                for obj in rel():
                    if not isinstance(obj, DeviceComponent): break
                    yield obj


    def getSnmpConnInfo(self):
        """
        Returns an object containing SNMP Connection Info
        
        @rtype: SnmpConnInfo object

        >>> from Products.ZenModel.Device import manage_addDevice
        >>> manage_addDevice(devices, 'test')
        >>> lst = devices.test.getSnmpConnInfo().__dict__.items()
        >>> lst.sort()
        >>> lst
        [('id', 'test'), ('manageIp', ''), ('zMaxOIDPerRequest', 40), ('zSnmpAuthPassword', ''), ('zSnmpAuthType', ''), ('zSnmpCommunity', 'public'), ('zSnmpMonitorIgnore', False), ('zSnmpPort', 161), ('zSnmpPrivPassword', ''), ('zSnmpPrivType', ''), ('zSnmpSecurityName', ''), ('zSnmpTimeout', 2.5), ('zSnmpTries', 2), ('zSnmpVer', 'v1')]
        """
        from Products.ZenHub.services.PerformanceConfig import SnmpConnInfo
        return SnmpConnInfo(self)


    def getHWManufacturerName(self):
        """
        DEPRECATED - Return the hardware manufacturer name of this device.
        
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.hw.getManufacturerName()


    def getHWProductName(self):
        """
        Return the hardware product name of this device.
        
        @rtype: string
        """
        return self.hw.getProductName()


    def getHWProductKey(self):
        """
        DEPRECATED - Return the productKey of the device hardware.
        
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.hw.getProductKey()


    def getOSManufacturerName(self):
        """
        DEPRECATED - Return the OS manufacturer name of this device.
        
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.os.getManufacturerName()


    def getOSProductName(self):
        """
        DEPRECATED - Return the OS product name of this device.
        
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.os.getProductName()


    def getOSProductKey(self):
        """
        DEPRECATED - Return the productKey of the device OS.
        
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.os.getProductKey()


    def setOSProductKey(self, prodKey):
        """
        Set the productKey of the device OS.
        """
        self.os.setProductKey(prodKey)


    def getHWTag(self):
        """
        DEPRECATED - Return the tag of the device HW.
        
        @rtype: string
        @todo: remove this method and remove the call from testDevice.py
        """
        return self.hw.tag


    def setHWTag(self, assettag):
        """
        Set the asset tag of the device hardware.
        """
        self.hw.tag = assettag


    def setHWProductKey(self, prodKey):
        """
        Set the productKey of the device hardware.
        """
        self.hw.setProductKey(prodKey)


    def setHWSerialNumber(self, number):
        """
        Set the hardware serial number.
        """
        self.hw.serialNumber = number


    def getHWSerialNumber(self):
        """
        DEPRECATED - Return the hardware serial number.
        
        @rtype: string
        @todo: Remove this method and remove the call from testDevice.py
        """
        return self.hw.serialNumber


    def followNextHopIps(self):
        """
        Return the ips that our indirect routs point to which aren't currently 
        connected to devices.
        
        @todo: Can be moved to zendisc.py
        """
        ips = []
        for r in self.os.routes():
            ipobj = r.nexthop()
            #if ipobj and not ipobj.device(): 
            if ipobj: ips.append(ipobj.id)
        return ips


    security.declareProtected(ZEN_VIEW, 'getLocationName')
    def getLocationName(self):
        """
        Return the full location name ie /Location/SubLocation/Rack
        
        @rtype: string
        @permission: ZEN_VIEW
        """
        loc = self.location()
        if loc: return loc.getOrganizerName()
        return ""
    
    security.declareProtected(ZEN_VIEW, 'getLocationLink')
    def getLocationLink(self):
        """
        Return a link to the device's location.
        
        @rtype: string
        @permission: ZEN_VIEW
        """
        loc = self.location()
        if loc: 
            if self.checkRemotePerm(ZEN_MANAGE_DMD, loc):
                return "<a href='%s'>%s</a>" % (loc.getPrimaryUrlPath(),
                                                loc.getOrganizerName())
            else:
                return loc.getOrganizerName()
        return "None"


    security.declareProtected(ZEN_VIEW, 'getSystemNames')
    def getSystemNames(self):
        """
        Return the system names for this device
        
        @rtype: list
        @permission: ZEN_VIEW
        """
        return map(lambda x: x.getOrganizerName(), self.systems())


    security.declareProtected(ZEN_VIEW, 'getSystemNamesString')
    def getSystemNamesString(self, sep=', '):
        """
        Return the system names for this device as a string

        @rtype: string
        @permission: ZEN_VIEW
        """
        return sep.join(self.getSystemNames())


    security.declareProtected(ZEN_VIEW, 'getDeviceGroupNames')
    def getDeviceGroupNames(self):
        """
        Return the device group names for this device
        
        @rtype: list
        @permission: ZEN_VIEW
        """
        return map(lambda x: x.getOrganizerName(), self.groups())


    security.declareProtected(ZEN_VIEW, 'getPerformanceServer')
    def getPerformanceServer(self):
        """
        Return the device performance server
        
        @rtype: PerformanceMonitor
        @permission: ZEN_VIEW
        """
        return self.perfServer()


    security.declareProtected(ZEN_VIEW, 'getPerformanceServerName')
    def getPerformanceServerName(self):
        """
        Return the device performance server name
        
        @rtype: string
        @permission: ZEN_VIEW
        """
        cr = self.perfServer()
        if cr: return cr.getId()
        return ''


    def getNetworkRoot(self):
        """Return the network root object
        """
        return self.getDmdRoot('Networks')

    security.declareProtected(ZEN_VIEW, 'getLastChange')
    def getLastChange(self):
        """
        Return DateTime of last change detected on this device.
        
        @rtype: DateTime
        @permission: ZEN_VIEW
        """
        return DateTime(float(self._lastChange))

    
    security.declareProtected(ZEN_VIEW, 'getLastChangeString')
    def getLastChangeString(self):
        """
        Return date string of last change detected on this device.
        
        @rtype: string
        @permission: ZEN_VIEW
        """
        return Time.LocalDateTime(float(self._lastChange))


    security.declareProtected(ZEN_VIEW, 'getSnmpLastCollection')
    def getSnmpLastCollection(self):
        """
        Return DateTime of last SNMP collection on this device.
        
        @rtype: DateTime
        @permission: ZEN_VIEW
        """
        return DateTime(float(self._snmpLastCollection))


    security.declareProtected(ZEN_VIEW, 'getSnmpLastCollectionString')
    def getSnmpLastCollectionString(self):
        """
        Return date string of last SNMP collection on this device.
        
        @rtype: string
        @permission: ZEN_VIEW
        """
        return Time.LocalDateTime(float(self._snmpLastCollection))


    security.declareProtected(ZEN_ADMIN_DEVICE, 'setManageIp')
    def setManageIp(self, ip="", REQUEST=None):
        """
        Set the manage IP, if IP is not passed perform DNS lookup.
        
        @rtype: string
        @permission: ZEN_ADMIN_DEVICE
        """
        try:
            if ip.find("/") > -1: 
                ipWithoutNetmask, netmask = ip.split("/",1)
                checkip(ipWithoutNetmask)
                # Also check for valid netmask
                if maskToBits(netmask) is None: ip = ""
            else:
                checkip(ip)
        except IpAddressError: ip = ""
        except ValueError: ip = ""
        if not ip:
            try: ip = socket.gethostbyname(self.id)
            except socket.error: ip = ""
        self.manageIp = ip
        self.index_object()
        if REQUEST:
            if ip: REQUEST['message'] = "Manage IP set"
            else: REQUEST['message'] = "Not a valid IP"
            return self.callZenScreen(REQUEST)
        else:
            return self.manageIp


    security.declareProtected(ZEN_VIEW, 'getManageIp')
    def getManageIp(self):
        """
        Return the management ip for this device.
        
        @rtype: string
        @permission: ZEN_VIEW
        """
        return self.manageIp

    
    def getManageIpObj(self):
        """
        DEPRECATED - Return the management ipobject for this device.
        
        @rtype: IpAddress
        @todo: This method may not be called anywhere, remove it.
        """
        if self.manageIp:
            return self.Networks.findIp(self.manageIp)


    security.declareProtected(ZEN_VIEW, 'getManageInterface')
    def getManageInterface(self):
        """
        Return the management interface of a device based on its manageIp.
        
        @rtype: IpInterface
        @permission: ZEN_VIEW
        """
        ipobj = self.Networks.findIp(self.manageIp)
        if ipobj: return ipobj.interface()


    security.declareProtected(ZEN_VIEW, 'uptimeStr')
    def uptimeStr(self):
        """
        Return the SNMP uptime
        
        @rtype: string
        @permission: ZEN_VIEW
        """
        ut = self.sysUpTime()
        if ut < 0:
            return "Unknown"
        elif ut == 0:
            return "0d:0h:0m:0s"
        ut = float(ut)/100.
        days = ut/86400
        hour = (ut%86400)/3600
        mins = (ut%3600)/60
        secs = ut%60
        return "%02dd:%02dh:%02dm:%02ds" % (
            days, hour, mins, secs)


    def getPeerDeviceClassNames(self):
        """
        Build a list of all device paths that have the python class pyclass
        
        @rtype: list
        """
        dclass = self.getDmdRoot("Devices")
        return dclass.getPeerDeviceClassNames(self.__class__)


    security.declareProtected(ZEN_VIEW, 'getRouterGraph')
    def getRouterGraph(self):
        """
        Return a graph representing the relative routers
        
        @rtype: graph
        @permission: ZEN_VIEW
        """
        from Products.ZenStatus import pingtree
        node = pingtree.buildTree(self)
        g = NetworkGraph(node=node, parentName=self.id)
        #g.format = 'svg'
        self.REQUEST.RESPONSE.setHeader('Content-Type', 'image/%s' % g.format)
        return g.render()


    security.declareProtected(ZEN_VIEW, 'getNetworkGraph')
    def getNetworkGraph(self):
        """
        Return a graph representing the relative routers as well as the
        networks
        
        @rtype: graph
        @permission: ZEN_VIEW
        """
        from Products.ZenStatus import pingtree
        node = pingtree.buildTree(self)
        g = NetworkGraph(node=node, parentName=self.id)
        #g.format = 'svg'
        self.REQUEST.RESPONSE.setHeader('Content-Type', 'image/%s' % g.format)
        return g.render(withNetworks=True)
        
    ####################################################################
    # Edit functions used to manage device relations and other attributes
    ####################################################################

    security.declareProtected(ZEN_CHANGE_DEVICE, 'manage_snmpCommunity')
    def manage_snmpCommunity(self):
        """
        Reset the snmp community using the zSnmpCommunities variable.
        
        @permission: ZEN_CHANGE_DEVICE
        """
        try:
            zSnmpCommunity, zSnmpPort, zSnmpVer, snmpname = \
                findCommunity(self, self.manageIp, self.getDeviceClassPath(),
                            port=self.zSnmpPort, version=self.zSnmpVer)
        except NoSnmp:
            pass
        else:
            if self.zSnmpCommunity != zSnmpCommunity:
                self.setZenProperty("zSnmpCommunity", zSnmpCommunity)
            if self.zSnmpPort != zSnmpPort:
                self.setZenProperty("zSnmpPort", zSnmpPort)
            if self.zSnmpVer != zSnmpVer:
                self.setZenProperty("zSnmpVer", zSnmpVer)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'manage_editDevice')
    def manage_editDevice(self,
                tag="", serialNumber="",
                zSnmpCommunity="", zSnmpPort=161, zSnmpVer="",
                rackSlot=0, productionState=1000, comments="",
                hwManufacturer="", hwProductName="",
                osManufacturer="", osProductName="",
                locationPath="", groupPaths=[], systemPaths=[],
                performanceMonitor="localhost",
                priority=3, REQUEST=None):
        """
        Edit the device relation and attributes.
        
        @param locationPath: path to a Location
        @type locationPath: string
        @param groupPaths: paths to DeviceGroups
        @type groupPaths: list
        @param systemPaths: paths to Systems
        @type systemPaths: list
        @param performanceMonitor: name of PerformanceMonitor
        @type performanceMonitor: string
        @permission: ZEN_CHANGE_DEVICE
        """
        self.hw.tag = tag
        self.hw.serialNumber = serialNumber
        unused(zSnmpCommunity, zSnmpVer, zSnmpPort)
        for prop in ('zSnmpCommunity', 'zSnmpVer', 'zSnmpPort'):
            passedIn = locals()[prop]
            if passedIn and getattr(self, prop) != passedIn:
                self.setZenProperty(prop, passedIn)

        self.rackSlot = rackSlot
        self.setProdState(productionState)
        self.setPriority(priority)
        self.comments = comments

        if hwManufacturer and hwProductName:
            log.info("setting hardware manufacturer to %s productName to %s"
                            % (hwManufacturer, hwProductName))
            self.hw.setProduct(hwProductName, hwManufacturer)
        else:
            self.hw.productClass.removeRelation()

        if osManufacturer and osProductName:
            log.info("setting os manufacturer to %s productName to %s"
                            % (osManufacturer, osProductName))
            self.os.setProduct(osProductName, osManufacturer)
            self.os.productClass().isOS = True
        else:
            self.os.productClass.removeRelation()

        if locationPath:
            log.info("setting location to %s" % locationPath)
            self.setLocation(locationPath)

        if groupPaths:
            log.info("setting group %s" % groupPaths)
            self.setGroups(groupPaths)

        if systemPaths:
            log.info("setting system %s" % systemPaths)
            self.setSystems(systemPaths)

        if performanceMonitor != self.getPerformanceServerName():
            log.info("setting performance monitor to %s" % performanceMonitor)
            self.setPerformanceMonitor(performanceMonitor)
       
        self.setLastChange()
        self.index_object()
        if REQUEST:
            from Products.ZenUtils.Time import SaveMessage
            REQUEST['message'] = SaveMessage()
            return self.callZenScreen(REQUEST)


    def monitorDevice(self):
        """
        Returns true if the device production state >= zProdStateThreshold.
        
        @rtype: boolean
        """
        return self.productionState >= self.zProdStateThreshold


    def snmpMonitorDevice(self):
        """
        Returns true if the device is subject to SNMP monitoring
        
        @rtype: boolean
        """
        return (self.monitorDevice()
                and not self.zSnmpMonitorIgnore
                and (self.zSnmpCommunity or
                     getattr(self, 'zSnmpSecurityName', None)))


    def getProductionStateString(self):
        """
        Return the prodstate as a string.
        
        @rtype: string
        """
        return self.convertProdState(self.productionState)


    def getPriority(self):
        """
        Return the numeric device priority.

        @rtype: int
        """
        return self.priority


    def getPriorityString(self):
        """
        Return the device priority as a string.
        
        @rtype: string
        """
        return self.convertPriority(self.priority)
        
    def getPingStatusString(self):
        """
        Return the pingStatus as a string
        
        @rtype: string
        """
        return self.convertStatus(self.getPingStatus())

    def getSnmpStatusString(self):
        """
        Return the snmpStatus as a string
        
        @rtype: string
        """
        return self.convertStatus(self.getSnmpStatus())

    security.declareProtected(ZEN_CHANGE_DEVICE, 'setProdState')
    def setProdState(self, state, REQUEST=None):
        """
        Set the device's production state.
        
        @type state: int
        @permission: ZEN_CHANGE_DEVICE
        """
        self.productionState = int(state)
        self.primaryAq().index_object()
        try:
            zem = self.dmd.ZenEventManager
            conn = zem.connect()
            try:
                curs = conn.cursor()
                curs.execute(
                    "update status set prodState=%d where device='%s'" % (
                    self.productionState, self.id))
            finally: zem.close(conn)
        except OperationalError:
            log.exception("failed to update events with new prodState")
            if REQUEST:
                REQUEST['message'] = "Failed to update events with new production state"
                return self.callZenScreen(REQUEST)
                
        if REQUEST:
            REQUEST['message'] = "Production state set"
            return self.callZenScreen(REQUEST)
    
    security.declareProtected(ZEN_CHANGE_DEVICE, 'setPriority')
    def setPriority(self, priority, REQUEST=None):
        """ 
        Set the device's priority

        @type priority: int
        @permission: ZEN_CHANGE_DEVICE
        """
        self.priority = int(priority)
        try:
            zem = self.dmd.ZenEventManager
            conn = zem.connect()
            try:
                curs = conn.cursor()
                curs.execute("update status set DevicePriority=%d where device='%s'" % (
                                self.priority, self.id))
            finally: zem.close(conn)
        except OperationalError:
            log.exception("failed to update events with new priority")
            if REQUEST:
                REQUEST['message'] = "Failed to update events with new priority"
                return self.callZenScreen(REQUEST)
                
        if REQUEST:
            REQUEST['message'] = "Priority set"
            return self.callZenScreen(REQUEST)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'setLastChange')
    def setLastChange(self, value=None):
        """
        Set the changed datetime for this device. 
        
        @param value: secs since the epoch, default is now
        @type value: float
        @permission: ZEN_CHANGE_DEVICE 
        """
        if value is None:
            value = time.time()
        self._lastChange = float(value)

    security.declareProtected(ZEN_CHANGE_DEVICE, 'setSnmpLastCollection')
    def setSnmpLastCollection(self, value=None):
        """
        Set the last time snmp collection occurred.
        
        @param value: secs since the epoch, default is now
        @type value: float
        @permission: ZEN_CHANGE_DEVICE
        """
        if value is None:
            value = time.time()
        self._snmpLastCollection = float(value)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'addManufacturer')
    def addManufacturer(self, newHWManufacturerName=None,
                        newSWManufacturerName=None, REQUEST=None):
        """
        DEPRECATED -
        Add either a hardware or software manufacturer to the database. 
        
        @permission: ZEN_CHANGE_DEVICE
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
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


    security.declareProtected(ZEN_CHANGE_DEVICE, 'setHWProduct')
    def setHWProduct(self, newHWProductName=None, hwManufacturer=None, 
                        REQUEST=None):
        """
        DEPRECATED -
        Adds a new hardware product
        
        @permission: ZEN_CHANGE_DEVICE
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
        added = False
        if newHWProductName and hwManufacturer:
            self.getDmdRoot("Manufacturers").createHardwareProduct(
                                        newHWProductName, hwManufacturer)
            added = True
        if REQUEST:
            if added:
                REQUEST['message'] = "Hardware product set"
                REQUEST['hwProductName'] = newHWProductName
            else:
                REQUEST['message'] = "Hardware product was not set"
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'setOSProduct')
    def setOSProduct(self, newOSProductName=None, osManufacturer=None, REQUEST=None):
        """
        DEPRECATED
        Adds a new os product
        
        @permission: ZEN_CHANGE_DEVICE
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
        if newOSProductName:
            self.getDmdRoot("Manufacturers").createSoftwareProduct(
                                        newOSProductName, osManufacturer, isOS=True)
        if REQUEST:
            if newOSProductName:
                REQUEST['message'] = "OS Product set"
                REQUEST['osProductName'] = newOSProductName
            else:
                REQUEST['message'] = "OS Product was not set"
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'setLocation')
    def setLocation(self, locationPath, REQUEST=None):
        """
        Set the location of a device. If the location is new it will be created.
        
        @permission: ZEN_CHANGE_DEVICE
        """
        if not locationPath: 
            self.location.removeRelation()
        else:
            locobj = self.getDmdRoot("Locations").createOrganizer(locationPath)
            self.addRelation("location", locobj)
        self.setAdminLocalRoles()
        self.index_object()


    def addLocation(self, newLocationPath, REQUEST=None):
        """
        DEPRECATED
        Add a new location and relate it to this device
        
        @todo: Doesn't really do work on a device object.
        Already exists on ZDeviceLoader
        """
        self.getDmdRoot("Locations").createOrganizer(newLocationPath)
        if REQUEST:
            REQUEST['locationPath'] = newLocationPath
            REQUEST['message'] = "Added Location %s at time:" % newLocationPath
            return self.callZenScreen(REQUEST)
   

    security.declareProtected(ZEN_CHANGE_DEVICE, 'setPerformanceMonitor')
    def setPerformanceMonitor(self, performanceMonitor,
                            newPerformanceMonitor=None, REQUEST=None):
        """
        Set the performance monitor for this device.
        If newPerformanceMonitor is passed in create it
        
        @permission: ZEN_CHANGE_DEVICE
        """
        if newPerformanceMonitor:
            #self.dmd.RenderServer.moveRRDFiles(self.id,
            #    newPerformanceMonitor, performanceMonitor, REQUEST)
            performanceMonitor = newPerformanceMonitor
        
        obj = self.getDmdRoot("Monitors").getPerformanceMonitor(
                                                    performanceMonitor)
        self.addRelation("perfServer", obj)
        self.setLastChange()
                
        if REQUEST:
            REQUEST['message'] = "Set Performance %s at time:" % performanceMonitor
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'setGroups')
    def setGroups(self, groupPaths):
        """
        Set the list of groups for this device based on a list of paths
        
        @permission: ZEN_CHANGE_DEVICE
        """
        objGetter = self.getDmdRoot("Groups").createOrganizer
        self._setRelations("groups", objGetter, groupPaths)
        self.index_object()


    security.declareProtected(ZEN_CHANGE_DEVICE, 'addDeviceGroup')
    def addDeviceGroup(self, newDeviceGroupPath, REQUEST=None):
        """
        DEPRECATED?
        Add a device group to the database and this device

        @permission: ZEN_CHANGE_DEVICE
        @todo: Already exists on ZDeviceLoader
        """
        group = self.getDmdRoot("Groups").createOrganizer(newDeviceGroupPath)
        self.addRelation("groups", group)
        if REQUEST:
            REQUEST['message'] = "Added Group %s at time:" % newDeviceGroupPath
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'setSystems')
    def setSystems(self, systemPaths):
        """
        Set a list of systems to this device using their system paths

        @permission: ZEN_CHANGE_DEVICE
        """
        objGetter = self.getDmdRoot("Systems").createOrganizer
        self._setRelations("systems", objGetter, systemPaths)
        self.index_object()
      

    security.declareProtected(ZEN_CHANGE_DEVICE, 'addSystem')
    def addSystem(self, newSystemPath, REQUEST=None):
        """
        DEPRECATED?
        Add a systems to this device using its system path
        
        @permission: ZEN_CHANGE_DEVICE
        @todo: Already exists on ZDeviceLoader
        """
        sys = self.getDmdRoot("Systems").createOrganizer(newSystemPath)
        self.addRelation("systems", sys)
        if REQUEST:
            REQUEST['message'] = "System added"
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_CHANGE_DEVICE, 'setTerminalServer')
    def setTerminalServer(self, termservername):
        """
        Set the terminal server of this device
        
        @param termservername: device name of terminal server
        @permission: ZEN_CHANGE_DEVICE
        """
        termserver = self.findDevice(termservername)
        if termserver:
            self.addRelation('termserver', termserver)


    def _setRelations(self, relName, objGetter, relPaths):
        """
        Set related objects to this device
        
        @param relName: name of the relation to set
        @param objGetter: method to get the relation
        @param relPaths: list of relationship paths
        """
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
        self.setAdminLocalRoles()


    def getExpandedLinks(self):
        """
        Return the expanded zComment property
        
        @rtype: HTML output
        """
        from Products.ZenUtils.ZenTales import talesEval
        try:
            return talesEval('string:' + self.zLinks, self)
        except Exception, ex:
            import cgi
            return "<i class='errortitle'>%s</i>" % cgi.escape(str(ex))

    ####################################################################
    # Private getter functions that implement DeviceResultInt
    ####################################################################

    security.declareProtected(ZEN_VIEW, 'device')
    def device(self):
        """
        Support DeviceResultInt mixin class. Returns itself
        
        @permission: ZEN_VIEW
        """
        return self


    ####################################################################
    # Status Management Functions used by status monitors
    ####################################################################


    def pastSnmpMaxFailures(self):
        """
        Returns true if the device has more SNMP failures 
        than maxFailures on its status mon.
        
        @rtype: boolean
        """
        statusmon = self.monitors()
        if len(statusmon) > 0:
            statusmon = statusmon[0]
            return statusmon.maxFailures < self.getSnmpStatusNumber()
        return False


    # FIXME: cleanup --force option #2660
    security.declareProtected(ZEN_MANAGE_DEVICE_STATUS, 
        'getLastPollSnmpUpTime')
    def getLastPollSnmpUpTime(self):
        """
        Get the value of the snmpUpTime status object
        
        @permission: ZEN_MANAGE_DEVICE_STATUS
        """
        return self._lastPollSnmpUpTime.getStatus()


    # FIXME: cleanup --force option #2660
    security.declareProtected(ZEN_MANAGE_DEVICE_STATUS, 
        'setLastPollSnmpUpTime')
    def setLastPollSnmpUpTime(self, value):
        """
        Set the value of the snmpUpTime status object
        
        @permission: ZEN_MANAGE_DEVICE_STATUS
        """
        self._lastPollSnmpUpTime.setStatus(value)


    def snmpAgeCheck(self, hours):
        """
        Returns True if SNMP data was collected more than 24 hours ago
        """
        lastcoll = self.getSnmpLastCollection()
        hours = hours/24.0
        if DateTime() > lastcoll + hours: return 1


    def applyProductContext(self):
        """
        Apply zProperties inherited from Product Contexts.
        """
        self._applyProdContext(self.hw.getProductContext())
        self._applyProdContext(self.os.getProductContext())
        for soft in self.os.software():
            self._applyProdContext(soft.getProductContext())
        

    def _applyProdContext(self, context):
        """
        Apply zProperties taken for the product context passed in.
        
        @param context: list of tuples returned from 
        getProductContext on a MEProduct.
        """
        for name, value in context:
            if name == "zDeviceClass" and value:
                log.info("move device to %s", value)
                self.moveDevices(value, self.id)
            elif name == "zDeviceGroup" and value:
                log.info("add device to group %s", value)
                self.addDeviceGroup(value)
            elif name == "zSystem" and value:
                log.info("add device to system %s", value)
                self.addSystem(value)



    ####################################################################
    # Management Functions
    ####################################################################

    security.declareProtected(ZEN_MANAGE_DEVICE, 'collectDevice')
    def collectDevice(self, setlog=True, REQUEST=None, generateEvents=False):
        """
        Collect the configuration of this device AKA Model Device
        
        @param setlog: If true, set up the output log of this process
        @permission: ZEN_MANAGE_DEVICE
        @todo: generateEvents param is not being used.
        """
        unused(generateEvents)
        xmlrpc = isXmlRpc(REQUEST)
        perfConf = self.getPerformanceServer()
        perfConf.collectDevice(self, setlog, REQUEST)
        
        if xmlrpc: return 0


    security.declareProtected(ZEN_ADMIN_DEVICE, 'deleteDevice')
    def deleteDevice(self, deleteStatus=False, deleteHistory=False,
                    deletePerf=False, REQUEST=None):
        """
        Delete device from the database

        NB: deleteHistory is disabled for the 2.2 release.  In some
        circumstances it was causing many subprocesses to be spawned
        and creating a gridlock situation.

        @permission: ZEN_ADMIN_DEVICE
        """
        parent = self.getPrimaryParent()
        if deleteStatus:
            self.getEventManager().manage_deleteHeartbeat(self.getId())
            self.getEventManager().manage_deleteAllEvents(self.getId())
        # if deleteHistory:
        #     self.getEventManager().manage_deleteHistoricalEvents(self.getId())
        if deletePerf:
            self.getPerformanceServer().deleteRRDFiles(self.id)
        parent._delObject(self.getId())
        if REQUEST:
            if parent.getId()=='devices': 
                parent = parent.getPrimaryParent()
            REQUEST['RESPONSE'].redirect(parent.absolute_url() +
                                            "/deviceOrganizerStatus"
                                            '?message=Device deleted')


    security.declareProtected(ZEN_MANAGE_DEVICE, 'manage_deleteHeartbeat')
    def manage_deleteHeartbeat(self, REQUEST=None):
        """
        Delete this device's heartbeats.
        
        @permission: ZEN_MANAGE_DEVICE
        """
        self.getEventManager().manage_deleteHeartbeat(self.getId())
        if REQUEST:
            REQUEST['message'] = "Cleared heartbeat events for %s" % self.id
        return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_ADMIN_DEVICE, 'renameDevice')
    def renameDevice(self, newId=None, REQUEST=None):
        """
        Rename device from the DMD

        @permission: ZEN_ADMIN_DEVICE
        """
        if newId:
            if not isinstance(newId, unicode):
                newId = self.prepId(newId)
            parent = self.getPrimaryParent()
            parent.manage_renameObject(self.getId(), newId)
            self.setLastChange()
        if REQUEST: 
            REQUEST['message'] = "Device %s renamed to %s" % (self.getId(), newId)
            REQUEST['RESPONSE'].redirect("%s/%s" % (parent.absolute_url(), newId))
            

    def manage_afterAdd(self, item, container):
        """
        Device only propagates afterAdd if it is the added object.
        """
        super(Device,self).manage_afterAdd(item, container)
        self.index_object()


    def manage_afterClone(self, item):
        """
        DEPRECATED
        """
        super(Device,self).manage_afterClone(item)
        self.index_object()


    def manage_beforeDelete(self, item, container):
        """
        Device only propagates beforeDelete if we are being deleted or copied.
        Moving and renaming don't propagate.
        """
        super(Device,self).manage_beforeDelete(item, container)
        self.unindex_object()


    def cacheComponents(self):
        """
        Read current RRD values for all of a device's components
        """
        paths = self.getRRDPaths()[:]
        #FIXME need better way to scope and need to get DataSources 
        # from RRDTemplates
        #for c in self.os.interfaces(): paths.extend(c.getRRDPaths())
        for c in self.os.filesystems(): paths.extend(c.getRRDPaths())
        #for c in self.hw.harddisks(): paths.extend(c.getRRDPaths())
        objpaq = self.primaryAq()
        perfServer = objpaq.getPerformanceServer()
        if perfServer:
            try:
                result = perfServer.currentValues(paths)
                if result:
                    RRDView.updateCache(zip(paths, result))
            except Exception:
                log.exception("Unable to cache values for %s", self.id);


    def getUserCommandTargets(self):
        """
        Called by Commandable.doCommand() to ascertain objects on which
        a UserCommand should be executed.
        """
        return [self]

    def getUserCommandEnvironment(self):
        """
        Returns the tales environment used to evaluate the command
        """
        environ = Commandable.getUserCommandEnvironment(self)
        context = self.primaryAq()
        environ.update({'dev': context,  'device': context,})
        return environ
        
    def getUrlForUserCommands(self):
        """
        Returns a URL to redirect to after a command has executed
        used by Commandable
        """
        return self.getPrimaryUrlPath() + '/deviceManagement'

    def getHTMLEventSummary(self, severity=4):
        """
        Returns HTML Event Summary of a device
        """
        html = []
        html.append("<table width='100%' cellspacing='1' cellpadding='3'>")
        html.append("<tr>")
        def evsummarycell(ev):
            if ev[1]-ev[2]>=0: klass = '%s empty thin' % ev[0]
            else: klass = '%s thin' % ev[0]
            h = '<th align="center" width="16%%" class="%s">%s/%s</th>' % (
                klass, ev[1], ev[2])
            return h
        info = self.getEventSummary(severity)
        html += map(evsummarycell, info)
        html.append('</tr></table>')
        return '\n'.join(html)

    def getDataForJSON(self):
        """
        Returns data ready for serialization
        """
        url, classurl = map(urlquote, 
                    (self.getDeviceUrl(), self.getDeviceClassPath()))
        id = '<a class="tablevalues" href="%s">%s</a>' % (
                            url, self.getId())
        ip = self.getDeviceIp()
        if self.checkRemotePerm(ZEN_MANAGE_DMD, self.deviceClass()):
            path = '<a href="/zport/dmd/Devices%s">%s</a>' % (classurl,classurl)
        else:
            path = classurl
        prod = self.getProdState()
        evsum = self.getHTMLEventSummary()
        return [id, ip, path, prod, evsum, self.getId()]

    def exportXmlHook(self, ofile, ignorerels):
        """
        Add export of our child objects.
        """
        map(lambda o: o.exportXml(ofile, ignorerels), (self.hw, self.os))

    def zenPropertyOptions(self, propname):
        """
        Returns a list of possible options for a given zProperty
        """
        if propname == 'zCollectorPlugins':
            from Products.DataCollector.Plugins import loadPlugins
            names = [ldr.pluginName() for ldr in loadPlugins(self.dmd)]
            names.sort()
            return names
        if propname == 'zSnmpVer':
            return ['v1', 'v2c', 'v3']
        if propname == 'zSnmpAuthType':
            return ['', 'MD5', 'SHA']
        if propname == 'zSnmpPrivType':
            return ['', 'DES', 'AES']
        return ManagedEntity.zenPropertyOptions(self, propname)
    
    security.declareProtected(ZEN_MANAGE_DEVICE, 'pushConfig')
    def pushConfig(self, REQUEST=None):
        """
        This will result in a push of all the devices to live collectors
        
        @permission: ZEN_MANAGE_DEVICE
        """
        self._p_changed = True
        if REQUEST:
            REQUEST['message'] = 'Changes to %s pushed to collectors' % self.id
            return self.callZenScreen(REQUEST)
    
    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES, 'bindTemplates')
    def bindTemplates(self, ids=(), REQUEST=None):
        """
        This will bind available templates to the zDeviceTemplates
        
        @permission: ZEN_EDIT_LOCAL_TEMPLATES
        """
        return self.setZenProperty('zDeviceTemplates', ids, REQUEST)
    
    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES, 'removeZDeviceTemplates')
    def removeZDeviceTemplates(self, REQUEST=None):
        """
        Deletes the local zProperty, zDeviceTemplates
        
        @permission: ZEN_EDIT_LOCAL_TEMPLATES
        """
        for id in self.zDeviceTemplates:
            self.removeLocalRRDTemplate(id)
        return self.deleteZenProperty('zDeviceTemplates', REQUEST)
    
    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES, 'addLocalTemplate')
    def addLocalTemplate(self, id, REQUEST=None):
        """
        Create a local template on a device
        
        @permission: ZEN_EDIT_LOCAL_TEMPLATES
        """
        from Products.ZenModel.RRDTemplate import manage_addRRDTemplate
        manage_addRRDTemplate(self, id)
        if id not in self.zDeviceTemplates:
            self.bindTemplates(self.zDeviceTemplates+[id])
        if REQUEST:
            REQUEST['message'] = 'Added template %s to %s' % (id, self.id)
            return self.callZenScreen(REQUEST)

    def getAvailableTemplates(self):
        """
        Returns all available templates for this device
        """
        # All templates defined on this device are available
        templates = self.objectValues('RRDTemplate')
        # Any templates available to the class that aren't overridden locally
        # are also available
        templates += [t for t in self.deviceClass().getRRDTemplates()
                        if t.id not in [r.id for r in templates]]
        def cmpTemplates(a, b):
            return cmp(a.id.lower(), b.id.lower())
        templates.sort(cmpTemplates)
        return templates

    security.declareProtected(ZEN_VIEW, 'getLinks')
    def getLinks(self, OSI_layer='3'):
        """
        Returns all Links on this Device's interfaces
        
        @permission: ZEN_VIEW
        """
        if OSI_layer=='3': 
            from Products.ZenUtils.NetworkTree import getDeviceNetworkLinks
            for link in getDeviceNetworkLinks(self):
                yield link
        else:
            for iface in self.os.interfaces.objectValuesGen():
                for link in iface.links.objectValuesGen():
                    yield link

    security.declareProtected(ZEN_VIEW, 'getXMLEdges')
    def getXMLEdges(self, depth=3, filter="/", start=()):
        """
        Gets XML
        """
        if not start: start=self.id
        edges = NetworkTree.get_edges(self, depth, 
                                      withIcons=True, filter=filter)
        return edgesToXML(edges, start)

    security.declareProtected(ZEN_VIEW, 'getPrettyLink')
    def getPrettyLink(self):
        """
        Gets a link to this device, plus an icon
        
        @rtype: HTML text
        @permission: ZEN_VIEW
        """
        template = ("<div class='device-icon-container'>"
                    "<img class='device-icon' src='%s'/> "
                    "</div>%s")
        icon = self.getIconPath()
        href = self.getPrimaryUrlPath().replace('%','%%')
        name = self.id
        linktemplate = "<a href='"+href+"' class='prettylink'>%s</a>"
        rendered = template % (icon, name)
        if not self.checkRemotePerm(ZEN_MANAGE_DMD, self):
            return rendered
        else:
            return linktemplate % rendered

    security.declareProtected(ZEN_VIEW, 'getEventPill')
    def getEventPill(self, showGreen=True):
        """
        Gets an event pill representing the highest severity
        See EventManagerBase.getEventPillME

        @rtype: JSON data
        @permission: ZEN_VIEW
        """
        pill = self.ZenEventManager.getEventPillME(self, showGreen=showGreen)
        if type(pill)==type([]) and len(pill)==1: return pill[0]
        return pill

    def getDeviceComponentEventSummary(self):
        """
        Gets datatable-ready string of components and summaries.
        See EventManagerBase.getDeviceComponentEventSummary
        
        @rtype: JSON data
        """
        return self.dmd.ZenEventManager.getDeviceComponentEventSummary(self)


    def updateProcesses(self, relmaps):
        "Uses ProcessClasses to create processes to monitor"

        from Products.DataCollector.ApplyDataMap import ApplyDataMap

        processes = self.getDmdRoot("Processes")
        pcs = list(processes.getSubOSProcessClassesGen())
	log.debug("zenoss processes: %s" % pcs)
        pcs.sort(lambda a, b: cmp(a.sequence,b.sequence))
      
	#some debug output 
        procs = Set()
	if log.isEnabledFor(10):
	    log.debug("=== snmp process information received ===")
	    for p in scanResults:
		log.debug("process: %s" % p)
	    log.debug("=== processes stored/defined in Zenoss ===")
	    for p in pcs:
		log.debug("%s\t%s" % (p.id, p.regex))

        procs = Set()
	
	#get the processes defined in Zenoss
        processes = self.getDmdRoot("Processes")
        pcs = list(processes.getSubOSProcessClassesGen())
	log.debug("zenoss processes: %s" % pcs)
        pcs.sort(lambda a, b: cmp(a.sequence,b.sequence))
      
	#some debug output 
	if log.isEnabledFor(10):
	    log.debug("=== snmp process information received ===")
	    for p in scanResults:
		log.debug("process: %s" % p)
	
	    log.debug("=== processes stored/defined in Zenoss ===")
	    for p in pcs:
		log.debug("%s\t%s" % (p.id, p.regex))

        maps = []
	for om in relmap.maps:
            om = ObjectMap(proc)
            fullname = (om.procName + " " + om.parameters).rstrip()
	    log.debug("current process: %s" % fullname)
            
	    for pc in pcs:
                if pc.match(fullname):
                    om.setOSProcessClass = pc.getPrimaryDmdId()
                    id = om.procName
                    parameters = om.parameters.strip()
                    if parameters and not pc.ignoreParameters:
                        parameters = md5.md5(parameters).hexdigest()
                        id += ' ' + parameters
                    om.id = self.prepId(id)
                    if id not in procs:
                        procs.add(id)
			log.debug("adding %s" % fullname)
                        maps.append(om)
                    break
        relmap.maps = maps

        adm = ApplyDataMap()
        return adm._applyDataMap(self, relmap)


InitializeClass(Device)
