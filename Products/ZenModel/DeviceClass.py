#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceClass

$Id: DeviceClass.py,v 1.76 2004/04/22 19:09:53 edahl Exp $"""

__version__ = "$Revision: 1.76 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base, aq_parent, aq_chain

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.CMFCore import permissions

from Products.ZenUtils.Utils import getObjByPath

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



class DeviceClass(DeviceOrganizer, Folder):
    """
    DeviceClass is a device organizer that manages the primary classification
    of device objects within the zenmon system.  It manages properties
    that are inherited through acquisition that modify the behavior of
    many different sub systems within zenmon.
    It also handles the creation of new devices in the system.
    """
   
    # Organizer configuration
    dmdRootName = "Devices"

    manageDeviceSearch = DTMLFile('dtml/manageDeviceSearch',globals())
    manageDeviceSearchResults = DTMLFile('dtml/manageDeviceSearchResults',
                                            globals())

    portal_type = meta_type = "DeviceClass"
    
    manage_main = Folder.manage_main

    manage_options = Folder.manage_options[:-1] + (
        {'label' : 'Find', 'action' : 'manageDeviceSearch'},)

    #Used to find factory on instance creation
    baseModulePath = "Products.ZenModel"  

    class_default_catalog = 'deviceSearch'

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
                  permissions.View, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'deviceClassEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'deviceClassHistoryEvents'
                , 'permissions'   : (
                  permissions.View, )
                },
                { 'id'            : 'config'
                , 'name'          : 'Config'
                , 'action'        : 'viewDeviceClassConfig'
                , 'permissions'   : (
                  permissions.View, )
                },
            )
         },
        )

    security = ClassSecurityInfo()

    
    def getPeerDeviceClassNames(self, pyclass):
        "build a list of all device paths that have the python class pyclass"
        dcnames = []
        if pyclass == self.getPythonDeviceClass():
            dcnames.append(self.getOrganizerName())
        for subclass in self.children():
            dcnames.extend(subclass.getPeerDeviceClassNames(pyclass))
        return dcnames
            

    def createInstance(self, id):
        """create an instance based on its location in the device tree
        walk up the primary aq path looking for a python instance class that
        matches the name of the closest node in the device tree"""
        pyClass = self.getPythonDeviceClass()
        dev = pyClass(id)
        self.devices._setObject(id, aq_base(dev))
        return self.devices._getOb(id)

    
    def getPythonDeviceClass(self):
        """return the python class object for this device class"""
        import sys
        from Device import Device
        modpath = self.baseModulePath
        aqpath = list(self.getPrimaryPath())
        aqpath.reverse()
        for name in aqpath:
            fullpath = ".".join((modpath, name))
            if sys.modules.has_key(fullpath):
                mod = sys.modules[fullpath]
                if hasattr(mod, name):
                    return getattr(mod, name)
        return Device 


    def moveDeviceClass(self, deviceName, devicePath, REQUEST=None):
        """move the device to another device class a bunch if stuff must happen
        check to see if we need to change the python class of the device
        if so run buildRelations to add any missing relations
        run manage_afterAdd to set the primaryPath of this and other objects"""
        dev = self.devices._getOb(deviceName)
        assert(dev)
        if dev.getDeviceClassPath() == devicePath: return
        devclass = self.getDmdRoot("Devices").getOrganizer(devicePath)
        newPyDevClass = devclass.getPythonDeviceClass()
        if dev.__class__ != newPyDevClass:
            raise ValueError, \
                "Can't move %s to new path %s because it has a" \
                "different python class." % (deviceName, devicePath)
            #dev = dev.changePythonClass(newPyDevClass, devclass.devices) 
            #devclass.devices._setObject(dev.id, dev)
        else:
            clip = self.devices.manage_cutObjects(ids=(deviceName,))
            devclass.devices.manage_pasteObjects(clip)
        dev = devclass.devices._getOb(deviceName)
        if REQUEST: 
            REQUEST['RESPONSE'].redirect(dev.absolute_url())


    #need to decuple these two methods out to actions
    security.declareProtected('View', 'deviceClassEvents')
    def deviceClassEvents(self):
        """get the event list of this object"""
        self.REQUEST.set('ev_whereclause', "DeviceClass like '%s.*'" %
                                    self.getDeviceClassPath())
        return self.viewEvents(self.REQUEST)


    security.declareProtected('View', 'deviceClassHistoryEvents')
    def deviceClassHistoryEvents(self):
        """get the history event list of this object"""
        self.REQUEST.set('ev_whereclause', "DeviceClass like '%s%%'" %
                                    self.getDeviceClassPath())
        self.REQUEST.set('ev_orderby', "LastOccurrence desc")
        return self.viewHistoryEvents(self.REQUEST)


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
   

    security.declareProtected('View', 'searchDevices')
    def searchDevices(self, query=None):
        '''Returns the concatenation of a device name,
        ip and mac search on the list of devices'''
        
        zcatalog = self._getCatalog()
        if not query or not zcatalog: return []
        
        ips = self.Networks.ipSearch({'id':query})
        names = zcatalog({'id':query})
        return self._convertResultsToObj(ips + names)
   

    security.declareProtected('View', 'searchDeviceSummary')
    def searchDeviceSummary(self, query):
        """search device summary index and return device objects"""
        if not query: return []
        zcatalog = self._getCatalog()
        if not zcatalog: return []
        results = zcatalog({'summary':query})
        return self._convertResultsToObj(results)


    def _convertResultsToObj(self, results):
        devices = []
        myroot = self.getPhysicalRoot()
        for brain in results:
            devobj = getObjByPath(myroot, brain.getPrimaryUrlPath)
            devices.append(devobj)
        return devices

    security.declareProtected('View', 'getDeviceFromSearchResult')
    def getDeviceFromSearchResult(self, brain):
        if brain.has_key('getPrimaryUrlPath'):
            myroot = self.getPhysicalRoot()
            return getObjByPath(myroot, brain.getPrimaryUrlPath)


    def findDevice(self, devicename):
        """look up device in catalog and return it"""
        ret = self._getCatalog()({'id': devicename})
        if ret:
            devobj = getObjByPath(self.getPhysicalRoot(), 
                                ret[0].getPrimaryUrlPath)
            return devobj


    def findDevicePingStatus(self, devicename):
        """look up device in catalog and return its pingStatus"""
        dev = self.findDevice(devicename)
        if dev: return dev.getPingStatusNumber()


    def createCatalog(self):
        """make the catalog for device searching"""
        from Products.ZCatalog.ZCatalog import manage_addZCatalog
        # Make catalog for Devices
        manage_addZCatalog(self, self.class_default_catalog, 
                            self.class_default_catalog)
        zcat = self._getOb(self.class_default_catalog)
        makeConfmonLexicon(zcat)
        zcat.addIndex('id', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('id'))
        zcat.addIndex('summary', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('summary'))
        zcat.addColumn('getPrimaryUrlPath')
    
        # Make catalog for IpInterfaces
        interfaceSearch = "interfaceSearch"
        manage_addZCatalog(self, interfaceSearch, interfaceSearch)
        zcat = self._getOb(interfaceSearch)
        makeConfmonLexicon(zcat)
        zcat.addIndex('description', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('description'))
        zcat.addIndex('deviceName', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('getDeviceName'))
        zcat.addIndex('interfaceName', 'ZCTextIndex', 
                        extra=makeIndexExtraParams('getInterfaceName'))
        zcat.addColumn('getPrimaryUrlPath')
        

    def _makeLexicon(self, zcat):
        class __R:pass
        ws=__R()
        ws.name='Confmon splitter'
        ws.group='Word Splitter'
        cn=__R()
        cn.name='Case Normalizer'
        cn.group='Case Normalizer'
        manage_addLexicon(zcat, 'myLexicon', elements=(cn, ws,))


    def buildDeviceTreeProperties(self):
        devs = self.getDmdRoot("Devices")
        if getattr(aq_base(devs), "zSnmpCommunities", False): return

        # Snmp collection properties
        devs._setProperty("zSnmpCommunities", ["public", "private"], 
                            type="lines")
        devs._setProperty("zSnmpCollectorIgnoreMaps", [], type="lines")
        devs._setProperty("zSnmpCollectorCollectMaps", [], type="lines")
        devs._setProperty("zRouterMapCollectOnlyLocal", True, type="boolean")
        devs._setProperty("zRouterMapCollectOnlyIndirect", True, type="boolean")
        devs._setProperty("zInterfaceMapIgnoreTypes", [], type="lines")
        devs._setProperty("zInterfaceMapIgnoreNames", "")
        devs._setProperty("zFileSystemMapIgnoreTypes", [], type="lines")
        devs._setProperty("zFileSystemMapIgnoreNames", "")
        devs._setProperty("zSysedgeDiskMapIgnoreNames", "")

        # Cricket properties
        devs._setProperty("zCricketDeviceType", "")
        devs._setProperty("zCricketInterfaceMap", [], type="lines")
        devs._setProperty("zCricketInterfaceIgnoreNames", "")
        devs._setProperty("zCricketInterfaceIgnoreTypes", [], type="lines")

        # what is the management interface
        devs._setProperty("zManageInterfaceNames", 
                         ('Loopback0','Ethernet0','hme0','ge0','eth0'), 
                         type="lines")

        # Ping monitor properties
        devs._setProperty("zPingInterfaceName", "")
        devs._setProperty("zPingInterfaceDescription", "")

    
    def deviceTreePropertyIds(self, all=True):
        """Return list of device tree property names."""
        if all: 
            devs = self.getDmdRoot("Devices")
        else: 
            if self.id == "Devices": return []
            devs = aq_base(self)
        props = []
        for prop in devs.propertyIds():
            if not prop.startswith("z"): continue
            props.append(prop)
        props.sort()
        return props


    def deviceTreePropertyMap(self):
        """Return property mapping of device tree properties."""
        devs = self.getDmdRoot("Devices")
        pnames = self.deviceTreePropertyIds()
        pmap = []
        for pdict in devs.propertyMap():
            if pdict['id'] in pnames:
                pmap.append(pdict)
        pmap.sort(lambda x, y: cmp(x['id'], y['id']))
        return pmap
            

    def deviceTreePropertyString(self, id):
        """Return the value of a device tree property as a string"""
        value = getattr(self, id, "")
        devs = self.getDmdRoot("Devices")
        type = devs.getPropertyType(id)
        if type == "lines": 
            value = ", ".join(value)
        return value


    def deviceTreePropertyPath(self, id):
        """Return the primaryId of where a device tree property is found."""
        for obj in aq_chain(self):
            if getattr(aq_base(obj), id, _marker) != _marker:
                return obj.getPrimaryDmdId("Devices", "children")


    def setDeviceTreeProperty(self, propname, propvalue, REQUEST=None):
        """
        Add or set the value of the property propname on this node of 
        the device Class tree.
        """
        devs = self.getDmdRoot("Devices")
        ptype = devs.getPropertyType(propname)
        if ptype == "lines": 
            propvalue = propvalue.split(",")
            propvalue = map(lambda x: x.strip(), propvalue)
        if getattr(aq_base(self), propname, _marker) != _marker:
            self._updateProperty(propname, propvalue)
        else:
            self._setProperty(propname, propvalue, type=ptype)
        if REQUEST: return self.callZenScreen(REQUEST)

    
    def deleteDeviceTreeProperty(self, propname, REQUEST):
        """
        Delete device tree properties from the this DeviceClass object.
        """
        self._delProperty(propname)
        if REQUEST: return self.callZenScreen(REQUEST)
         



InitializeClass(DeviceClass)
