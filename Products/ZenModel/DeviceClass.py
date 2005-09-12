#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""DeviceClass

The device classification class.  default identifiers, screens,
and data collectors live here.

$Id: DeviceClass.py,v 1.76 2004/04/22 19:09:53 edahl Exp $"""

__version__ = "$Revision: 1.76 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from OFS.Folder import Folder
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base, aq_parent

from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.CMFCore import permissions

from Products.ZenUtils.Utils import getObjByPath

from SearchUtils import makeConfmonLexicon, makeIndexExtraParams
from Device import manage_addDevice
from Classification import Classification
from DeviceGroupInt import DeviceGroupInt


def manage_addDeviceClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = DeviceClass(id, title)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 



addDeviceClass = DTMLFile('dtml/addDeviceClass',globals())



class DeviceClass(Classification, DeviceGroupInt, Folder):
    
    manageDeviceSearch = DTMLFile('dtml/manageDeviceSearch',globals())
    manageDeviceSearchResults = DTMLFile('dtml/manageDeviceSearchResults',
                                            globals())

    portal_type = meta_type = "DeviceClass"
    
    manage_main = Folder.manage_main

    manage_options = Folder.manage_options[:-1] + (
        {'label' : 'Find', 'action' : 'manageDeviceSearch'},)

    #Instance types that this class allows
    sub_classes = ('DeviceClass', 'Device')
    
    #Used to find factory on instance creation
    baseModulePath = "Products.ZenModel"  

    #when this hierarchy is walked recusively use this name
    subObjectsName = "subclasses"

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
            'immediate_view' : 'viewDeviceClassOverview',
            'actions'        :
            ( 
                { 'id'            : 'overview'
                , 'name'          : 'Overview'
                , 'action'        : 'viewDeviceClassOverview'
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

    
    security.declareProtected('Change Device', 'manage_addDeviceClass')
    def manage_addDeviceClass(self, newDeviceClassPath, REQUEST=None):
        """add a device group to the database"""
        self.getOrganizer("Devices").getDeviceClass(newDeviceClassPath)
        if REQUEST: 
            REQUEST['RESPONSE'].redirect(REQUEST['HTTP_REFERER']) 
            


    security.declareProtected('Change Device', 'manage_deleteDeviceClasses')
    def manage_deleteDeviceClasses(self, deviceClassPaths, REQUEST=None):
        """add a device group to the database"""
        devices = self.getOrganizer("Devices")
        for devClassName in deviceClassPaths:
            devClass = devices.getDeviceClass(devClassName)
            parent = aq_parent(devClass)
            parent.removeRelation(devClass)
        if REQUEST: 
            REQUEST['RESPONSE'].redirect(REQUEST['HTTP_REFERER']) 
            


    def getDeviceClass(self, path):
        """get or create the device class passed in devicePath"""
        path = self.zenpathsplit(path)
        if path[0] != "Devices": path.insert(0,"Devices")
        name = self.zenpathjoin(path)
        devobj =  self.getHierarchyObj(self.getDmd(), name,
                            manage_addDeviceClass, relpath="subclasses")
        return devobj    
        
        
    def getDeviceClassNames(self):
        """build a list of the full paths of all sub locations""" 
        dcnames = [self.getDeviceClassName()]
        for subclass in self.subclasses():
            dcnames.extend(subclass.getDeviceClassNames())
        dcnames.sort()
        return dcnames


    def getPeerDeviceClassNames(self, pyclass):
        "build a list of all device paths that have the python class pyclass"
        dcnames = []
        if pyclass == self.getPythonDeviceClass():
            dcnames.append(self.getDeviceClassName())
        for subclass in self.subclasses():
            dcnames.extend(subclass.getPeerDeviceClassNames(pyclass))
        return dcnames
            

    def deleteDeviceClasses(self, deviceClasses):
        """
        Delete all device classes passed in the list deviceClasses
        """


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
        devclass = self.getOrganizer("Devices").getDeviceClass(devicePath)
        newPyDevClass = devclass.getPythonDeviceClass()
        if dev.__class__ != newPyDevClass:
            raise ValueError, \
                "Can't move %s to new path %s because it has a" \
                "different python class." % (deviceName, devicePath)
            #dev = dev.changePythonClass(newPyDevClass, devclass.devices) 
            #devclass.devices._setObject(dev.id, dev)
        else:
            clip = self.devices.manage_cutObjects(ids=(deviceName,))
            dev._moving=1
            devclass.devices.manage_pasteObjects(clip)
        dev = devclass.devices._getOb(deviceName)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(dev.absolute_url())


    def getAllCounts(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupInt.getAllCounts(self, "subclasses")

    
    def countDevices(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupInt.countDevices(self, "subclasses")

    
    def pingStatus(self):
        """aggrigate ping status for all devices in this group and below"""
        return DeviceGroupInt.pingStatus(self, "subclasses")

    
    def snmpStatus(self):
        """aggrigate snmp status for all devices in this group and below"""
        return DeviceGroupInt.snmpStatus(self, "subclasses")


    def getSubDevices(self, filter=None):
        """get all the devices under and instance of a DeviceGroup"""
        return DeviceGroupInt.getSubDevices(self, filter, "subclasses")

    
    def getDeviceClassPath(self):
        '''Return the full device class path in the form /ServerLinux
        we make sure that the /Devices part is taken out'''
        path = DeviceGroupInt.getDeviceGroupName(self)
        path = path.split("/")
        path.remove("Devices")
        return "/".join(path)

    getDeviceClassName = getDeviceClassPath


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
                systemNames.append(sys.getFullSystemName())
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


InitializeClass(DeviceClass)
