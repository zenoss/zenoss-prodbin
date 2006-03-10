#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceClass

$Id: DeviceClass.py,v 1.76 2004/04/22 19:09:53 edahl Exp $"""

__version__ = "$Revision: 1.76 $"[11:-2]

import types
import transaction
import DateTime

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base, aq_parent, aq_chain
from zExceptions import Redirect

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from AccessControl import Permissions as permissions

from Products.ZenRelations.RelSchema import *

from SearchUtils import makeConfmonLexicon, makeIndexExtraParams

from DeviceOrganizer import DeviceOrganizer

_marker = "__MARKER___"

def manage_addDeviceClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = DeviceClass(id, title)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 



addDeviceClass = DTMLFile('dtml/addDeviceClass',globals())



class DeviceClass(DeviceOrganizer):
    """
    DeviceClass is a device organizer that manages the primary classification
    of device objects within the zenoss system.  It manages properties
    that are inherited through acquisition that modify the behavior of
    many different sub systems within zenoss.
    It also handles the creation of new devices in the system.
    """
   
    # Organizer configuration
    dmdRootName = "Devices"

    manageDeviceSearch = DTMLFile('dtml/manageDeviceSearch',globals())
    manageDeviceSearchResults = DTMLFile('dtml/manageDeviceSearchResults',
                                            globals())

    portal_type = meta_type = event_key = "DeviceClass"

    manage_main = Folder.manage_main

    manage_options = Folder.manage_options[:-1] + (
        {'label' : 'Find', 'action' : 'manageDeviceSearch'},)

    #Used to find factory on instance creation
    baseModulePath = "Products.ZenModel"  

    default_catalog = 'deviceSearch'
    
    _relations = DeviceOrganizer._relations + (
        ("devices", ToManyCont(ToOne,"Device","deviceClass")),
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
        { 
            'id'             : 'DeviceClass',
            'meta_type'      : 'DeviceClass',
            'description'    : """Base class for all devices""",
            'icon'           : 'DeviceClass_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addDeviceClass',
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

    
    def getPeerDeviceClassNames(self, pyclass=None):
        "Return a list of all device paths that have the python class pyclass"
        if pyclass == None: 
            pyclass = self.getPythonDeviceClass()
            dclass = self.getDmdRoot("Devices")
            return dclass.getPeerDeviceClassNames(pyclass)
        dcnames = []
        if pyclass == self.getPythonDeviceClass():
            dcnames.append(self.getOrganizerName())
        for subclass in self.children():
            dcnames.extend(subclass.getPeerDeviceClassNames(pyclass))
        return dcnames
    deviceMoveTargets = getPeerDeviceClassNames
    childMoveTargets = getPeerDeviceClassNames


    def createInstance(self, id):
        """
        Create an instance based on its location in the device tree
        walk up the primary aq path looking for a python instance class that
        matches the name of the closest node in the device tree.
        """
        dev = self.findDevice(id)
        if dev: return dev
        pyClass = self.getPythonDeviceClass()
        dev = pyClass(id)
        self.devices._setObject(id, dev)
        return self.devices._getOb(id)

    
    def getPythonDeviceClass(self):
        """
        Return the python class object to be used for device instances in this 
        device class.  This is done by walking up the aq_chain of a deviceclass 
        to find a node that has the same name as a python class or has an 
        attribute named zPythonClass that matches a python class.
        """
        import sys
        from Device import Device
        for obj in aq_chain(self):
            if obj.meta_type != "DeviceClass": continue 
            if obj.id == "Devices": break
            cname = getattr(aq_base(obj), "zPythonClass", None)
            if not cname: cname = obj.id
            fullpath = ".".join((self.baseModulePath, cname))
            if sys.modules.has_key(fullpath):
                mod = sys.modules[fullpath]
                if hasattr(mod, cname):
                    return getattr(mod, cname)
        return Device 
   

    def moveDevices(self, moveTarget, deviceNames=None, REQUEST=None):
        """
        Override default moveDevices because this is a contained relation. 
        """
        if not moveTarget or not deviceNames: return self()
        target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
        if type(deviceNames) == types.StringType: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            dev._operation = 1 # moving object state
            self.devices._delObject(devname)
            target.devices._setObject(devname, dev)
            dev.setLastChange()
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())

    

    security.declareProtected('View', 'getEventDeviceInfo')
    def getEventDeviceInfo(self):
        """getEventDeviceInfo() -> return the info for NcoEventPopulator"""
        deviceInfo = {}
        for device in self.getSubDevices():
            systemNames = []
            for sys in device.systems.objectValuesAll():
                systemNames.append(sys.getOrganizerName())
            systemNames = "|".join(systemNames)
            location = device.getLocationName()
            if not location: location = "Unknown"
            deviceInfo[device.id] = (systemNames, location,
                                    device.productionState,
                                    device.getDeviceClassPath())
        return deviceInfo
  

    security.declareProtected('View', 'getDeviceInfo')
    def getDeviceWinInfo(self, lastPoll=0):
        """Return list of (devname,user,passwd,url) for each device.
        user and passwd are used to connect via wmi.
        """
        ffunc = None
        if lastPoll > 0:
            lastPoll = DateTime.DateTime(lastPoll)
            ffunc = lambda x: x.getLastChange() > lastPoll
        devinfo = []
        for dev in self.getSubDevices(devfilter=ffunc):
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            devinfo.append((dev.id,user,passwd,dev.absolute_url()))
        return devinfo
    
    
    def getWinServices(self):
        """Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0}) 
        """
        svcinfo = []
        allsvcs = {}
        for s in self.getSubComponents("WinService"):
            svcs=allsvcs.setdefault(s.hostname(),{})
            svcs[s.name()] = s.getStatus()
        for dev in self.getSubDevices():
            svcs = allsvcs.get(dev.getId(), {})
            if not svcs and not dev.zWinEventlog: continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            svcinfo.append((dev.id, user, passwd, svcs))
        return svcinfo


    security.declareProtected('View', 'searchDevices')
    def searchDevices(self, query=None, REQUEST=None):
        '''Returns the concatenation of a device name,
        ip and mac search on the list of devices'''
        
        zcatalog = self._getCatalog()
        if not query or not zcatalog: return []
        if not query.endswith("*"): query+="*"
        ips = None 
        try:
            ips = self.Networks.ipSearch({'id':query})
        except AttributeError: pass
        names = zcatalog({'id':query})
        if ips: names += ips
        if len(names) == 1:
            raise Redirect(names[0].getPrimaryId)
        return self._convertResultsToObj(names)
   

    security.declareProtected('View', 'searchDeviceSummary')
    def searchDeviceSummary(self, query):
        """search device summary index and return device objects"""
        if not query: return []
        zcatalog = self._getCatalog()
        if not zcatalog: return []
        results = zcatalog({'summary':query})
        return self._convertResultsToObj(results)


    security.declareProtected('View', 'searchInterfaces')
    def searchInterfaces(self, query):
        """search interfaces index and return interface objects"""
        if not query: return []
        zcatalog = getattr(self, 'interfaceSearch', None)
        if not zcatalog: return []
        results = zcatalog(query)
        return self._convertResultsToObj(results)


    def _convertResultsToObj(self, results):
        devices = []
        for brain in results:
            devobj = self.unrestrictedTraverse(brain.getPrimaryId)
            devices.append(devobj)
        return devices


    security.declareProtected('View', 'getDeviceFromSearchResult')
    def getDeviceFromSearchResult(self, brain):
        if brain.has_key('getPrimaryId'):
            return self.unrestrictedTraverse(brain.getPrimaryId)


    def findDevice(self, devicename):
        """look up device in catalog and return it"""
        ret = self._getCatalog()({'id': devicename})
        if ret:
            devobj = self.unrestrictedTraverse(ret[0].getPrimaryId)
            return devobj


    def findDevicePingStatus(self, devicename):
        """look up device in catalog and return its pingStatus"""
        dev = self.findDevice(devicename)
        if dev: return dev.getPingStatusNumber()

    
    def getSubComponents(self, meta_type="", monitored=True):
        """Return generator of components, by meta_type if specified.
        """
        zcat = getattr(self, "componentSearch", None)
        if zcat: 
            res = zcat({'meta_type': meta_type, 'monitored': monitored})
            for b in res:
                yield self.unrestrictedTraverse(b.getPrimaryId)


    def getMonitoredComponents(self):
        """Return monitored components for devices within this DeviceDeviceClass.
        """
        return self.getSubComponents()


    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        # Make catalog for Devices
        manage_addZCatalog(self, self.default_catalog, 
                            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        makeConfmonLexicon(zcat)
        zcat.addIndex('id', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('id'))
        zcat.addIndex('summary', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('summary'))
        zcat.addColumn('getPrimaryId')
    
        # Make catalog for IpInterfaces
        manage_addZCatalog(self, "interfaceSearch", "interfaceSearch")
        zcat = self._getOb("interfaceSearch")
        makeConfmonLexicon(zcat)
        zcat.addIndex('getDeviceName', 'FieldIndex')
        zcat.addIndex('macaddress', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('macaddress'))
        zcat.addIndex('description', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('description'))
        zcat.addIndex('interfaceName', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('getInterfaceName'))
        zcat.addColumn('getPrimaryId')
       
        # make catalog for device components
        manage_addZCatalog(self, "componentSearch", "componentSearch")
        zcat = self._getOb("componentSearch")
        zcat.addIndex('meta_type', 'FieldIndex')
        zcat.addIndex('monitored', 'FieldIndex')
        zcat.addColumn('getPrimaryId')
        

    def _makeLexicon(self, zcat):
        class __R:pass
        ws=__R()
        ws.name='Confmon splitter'
        ws.group='Word Splitter'
        cn=__R()
        cn.name='Case Normalizer'
        cn.group='Case Normalizer'
        manage_addLexicon(zcat, 'myLexicon', elements=(cn, ws,))


    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        transaction.savepoint()
        for dev in self.getSubDevicesGen():
            dev.index_object()
            for int in dev.os.interfaces():
                int.index_object()
            transaction.savepoint()
            for svc in dev.os.winservices():
                svc.index_object()
            transaction.savepoint()
            for svc in dev.os.ipservices():
                svc.index_object()
            transaction.savepoint()



    def buildDeviceTreeProperties(self):
        devs = self.getDmdRoot("Devices")
        if getattr(aq_base(devs), "zSnmpCommunities", False): return

        # map deviec class to python classs (seperate from device class name)
        devs._setProperty("zPythonClass", "")

        # Display the ifdescripion field or not
        devs._setProperty("zIfDescription", False, type="boolean")

        # Snmp collection properties
        devs._setProperty("zSnmpCommunities",["public", "private"],type="lines")
        devs._setProperty("zSnmpCommunity", "public")
        devs._setProperty("zSnmpPort", 161, type="int")
        devs._setProperty("zSnmpVer", "v1")
        devs._setProperty("zSnmpTries", 2, type="int")
        devs._setProperty("zSnmpTimeout", 2.5, type="float")
        devs._setProperty("zRouteMapCollectOnlyLocal", False, type="boolean")
        devs._setProperty("zRouteMapCollectOnlyIndirect", False, type="boolean")
        devs._setProperty("zInterfaceMapIgnoreTypes", "")
        devs._setProperty("zInterfaceMapIgnoreNames", "")
        devs._setProperty("zFileSystemMapIgnoreTypes", [], type="lines")
        devs._setProperty("zFileSystemMapIgnoreNames", "")
        devs._setProperty("zSysedgeDiskMapIgnoreNames", "")
        devs._setProperty("zIpServiceMapMaxPort", 1024, type="int")

        # Cricket properties
        devs._setProperty("zCricketDeviceType", "")
        devs._setProperty("zCricketInterfaceMap", [], type="lines")
        devs._setProperty("zCricketInterfaceIgnoreNames", "")
        devs._setProperty("zCricketInterfaceIgnoreTypes", [], type="lines")

        # Ping monitor properties
        devs._setProperty("zPingInterfaceName", "")
        devs._setProperty("zPingInterfaceDescription", "")

        # Status monitor properites
        devs._setProperty("zSnmpMonitorIgnore", False, type="boolean")
        devs._setProperty("zPingMonitorIgnore", False, type="boolean")

        # DataCollector properties
        devs._setProperty("zTransportPreference", "snmp")
        devs._setProperty("zCollectorIgnorePlugins", "")
        devs._setProperty("zCollectorCollectPlugins", "")
        devs._setProperty("zCollectorClientTimeout", 180, type="int")
        devs._setProperty("zCommandUsername", "")
        devs._setProperty("zCommandPassword", "")
        devs._setProperty("zCommandProtocol", "ssh")
        devs._setProperty("zCommandPort", 22, type="int")
        devs._setProperty("zCommandLoginTries", 1, type="int")
        devs._setProperty("zCommandLoginTimeout", 10.0, type="float")
        devs._setProperty("zCommandCommandTimeout", 10.0, type="float")
        devs._setProperty("zCommandSearchPath", [], type="lines")
        devs._setProperty("zCommandExistanceTest", "test -f %s")
        devs._setProperty("zTelnetLoginRegex", "ogin:.$")
        devs._setProperty("zTelnetPasswordRegex", "assword:")
        devs._setProperty("zTelnetSuccessRegexList", 
                            ['\$.$', '\#.$'], type="lines")
        devs._setProperty("zTelnetEnable", False, type="boolean")
        devs._setProperty("zTelnetEnableRegex", "assword:")
        devs._setProperty("zTelnetTermLength", True, type="boolean")
        devs._setProperty("zTelnetPromptTimeout", 10.0, type="float")

        # Windows WMI collector properties
        devs._setProperty("zWinUser", "")
        devs._setProperty("zWinPassword", "")
        #devs._setProperty("zWinServices", "")
        devs._setProperty("zWinEventlog", False, type="boolean")


InitializeClass(DeviceClass)
