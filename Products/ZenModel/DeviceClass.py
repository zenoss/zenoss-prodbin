#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""DeviceClass

$Id: DeviceClass.py,v 1.76 2004/04/22 19:09:53 edahl Exp $"""

__version__ = "$Revision: 1.76 $"[11:-2]

import os
import types
import time
import urllib
from sets import Set
from glob import glob
import transaction

import DateTime
from zExceptions import Redirect
from Globals import DTMLFile
from Globals import InitializeClass
from Globals import InitializeClass
from OFS.Folder import manage_addFolder
from Acquisition import aq_base, aq_parent, aq_chain
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from Products.AdvancedQuery import MatchGlob
from Products.ZenRelations.RelSchema import *
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from RRDTemplate import RRDTemplate
from SearchUtils import makeFieldIndex
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

    #manage_main = Folder.manage_main

    #manage_options = Folder.manage_options[:-1] + (
    #    {'label' : 'Find', 'action' : 'manageDeviceSearch'},)

    #Used to find factory on instance creation
    baseModulePath = "Products.ZenModel"  

    default_catalog = 'deviceSearch'
    
    _relations = DeviceOrganizer._relations + (
        ("devices", ToManyCont(ToOne,"Device","deviceClass")),
        ("rrdTemplates", ToManyCont(ToOne,"RRDTemplate","deviceClass")),
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
                , 'permissions'   : ( permissions.view, )
                },
                { 'id'            : 'devicelist'
                , 'name'          : 'Devices'
                , 'action'        : 'deviceList'
                , 'permissions'   : ( permissions.view, )
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (  permissions.view, )
                },
                { 'id'            : 'historyEvents'
                , 'name'          : 'History'
                , 'action'        : 'viewHistoryEvents'
                , 'permissions'   : (  permissions.view, )
                },
                { 'id'            : 'perfConfig'
                , 'name'          : 'PerfConf'
                , 'action'        : 'perfConfig'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'config'
                , 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : ("Change Device",)
                },
                { 'id'            : 'manage'
                , 'name'          : 'Manage'
                , 'action'        : 'deviceOrganizerManage'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (  permissions.view, )
                },
            )
         },
        )

    security = ClassSecurityInfo()

    
    security.declareProtected('View', 'zentinelTabs')
    def zentinelTabs(self, templateName):
        """Return a list of hashs that define the screen tabs for this object.
        [{'name':'Name','action':'template','selected':False},...]
        """
        tabs = super(DeviceClass, self).zentinelTabs(templateName)
        if self.getPrimaryId() == "/zport/dmd/Devices" and self.isManager():
            tab = {'action': 'editCustSchema', 'name':'Custom Schema'}
            if templateName == tab['action']:
                tab['selected'] = True
            tabs.insert(-1, tab)
        return tabs


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
  

    security.declareProtected('View', 'getDeviceWinInfo')
    def getDeviceWinInfo(self, lastPoll=0, eventlog=False):
        """Return list of (devname,user,passwd,url) for each device.
        user and passwd are used to connect via wmi.
        """
        ffunc = None
        starttime = time.time()
        if lastPoll > 0:
            lastPoll = DateTime.DateTime(lastPoll)
            ffunc = lambda x: x.getSnmpLastCollection() > lastPoll
        if eventlog:
            ffunc = lambda x: x.zWinEventlog
        devinfo = []
        for dev in self.getSubDevices(devfilter=ffunc):
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            sev = getattr(dev, 'zWinEventlogMinSeverity', '')
            devinfo.append((dev.id,user,passwd,sev,dev.absolute_url()))
        return starttime, devinfo
    
    
    def getWinServices(self):
        """Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0}) 
        """
        svcinfo = []
        allsvcs = {}
        for s in self.getSubComponents("WinService"):
            svcs=allsvcs.setdefault(s.hostname(),{})
            svcs[s.name()] = (s.getStatus(), s.zFailSeverity)
        for dev in self.getSubDevices():
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            svcs = allsvcs.get(dev.getId(), {})
            if not svcs and not dev.zWinEventlog: continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            svcinfo.append((dev.id, user, passwd, svcs))
        return svcinfo


    security.declareProtected('View', 'searchDevices')
    def searchDevices(self, query=None, REQUEST=None):
        """Returns the concatenation of a device name, ip and mac
        search on the list of devices.
        """
        zcatalog = self._getCatalog()
        if not query or not zcatalog:
            return []
        if not query.endswith("*"):
            query+="*"
        ips = None 
        query = MatchGlob('id', query)
        try:
            ips = self.Networks.ipSearch.evalAdvancedQuery(query)
        except AttributeError:
            pass
        names = zcatalog.evalAdvancedQuery(query)
        if ips:
            names += ips
        if len(names) == 1:
            raise Redirect(urllib.quote(names[0].getPrimaryId))
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
        query = MatchGlob('id', devicename)
        ret = self._getCatalog().evalAdvancedQuery(query)
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
        """Return monitored components for devices within this DeviceDeviceClass
        """
        return self.getSubComponents()


    security.declareProtected('View', 'getImportFilesData')
    def getImportFilesData(self):
        """Get a list of XML filenames and basenames from the ZENHOME/import
        directory.
        """
        path = os.path.join(os.getenv('ZENHOME'), 'import')
        filedata = []
        for filename in glob(path+os.path.sep+'*.xml'):
            basename = os.path.basename(filename)
            filedata.append({
                'filename': filename,
                'display': basename})
        filedata.sort()
        return filedata


    security.declareProtected('View', 'getRRDImportFilesData')
    def getRRDImportFilesData(self):
        """Get a list of command-only import files' data.
        """
        return [ x for x in self.getImportFilesData() if 'RRD' in x['display'] ]


    security.declareProtected('View', 'getRRDTemplates')
    def getRRDTemplates(self, context=None):
        """Return the actual RRDTemplate instances.
        """
        templates = {}
        if not context: context = self
        mychain = aq_chain(context)
        mychain.reverse()
        for obj in mychain:
            if not getattr(aq_base(obj), 'rrdTemplates', False): continue
            for t in obj.rrdTemplates():
                templates[t.id] = t
        return templates.values()
            

    security.declareProtected('Add DMD Objects', 'manage_addRRDTemplate')
    def manage_addRRDTemplate(self, id, REQUEST=None):
        """Add an RRDTemplate to this DeviceClass.
        """
        if not id: return self.callZenScreen(REQUEST)
        id = self.prepId(id)
        org = RRDTemplate(id)
        self.rrdTemplates._setObject(org.id, org)
        if REQUEST: return self.callZenScreen(REQUEST)
            

    def manage_copyRRDTemplates(self, ids=(), REQUEST=None):
        """Put a reference to the objects named in ids in the clip board"""
        if not ids: return self.callZenScreen(REQUEST)
        ids = [ id for id in ids if self.rrdTemplates._getOb(id, None) != None]
        if not ids: return self.callZenScreen(REQUEST)
        cp = self.rrdTemplates.manage_copyObjects(ids)
        if REQUEST:
            resp=REQUEST['RESPONSE']
            resp.setCookie('__cp', cp, path='/zport/dmd')
            REQUEST['__cp'] = cp
            return self.callZenScreen(REQUEST)
        return cp


    def manage_pasteRRDTemplates(self, cb_copy_data=None, REQUEST=None):
        """Paste RRDTemplates that have been copied before.
        """
        cp = None
        if cb_copy_data: cp = cb_copy_data
        elif REQUEST:
            cp = REQUEST.get("__cp",None)
        if cp: self.rrdTemplates.manage_pasteObjects(cp)
        if REQUEST:
            REQUEST['RESPONSE'].setCookie('__cp', 'deleted', path='/zport/dmd',
                            expires='Wed, 31-Dec-97 23:59:59 GMT')
            REQUEST['__cp'] = None
            return self.callZenScreen(REQUEST)


    def manage_deleteRRDTemplates(self, ids=(), REQUEST=None):
        """Delete RRDTemplates from this DeviceClass 
        (skips ones in other Classes)
        """
        if not ids:
            return self.callZenScreen(REQUEST)
        for id in ids:
            if (getattr(aq_base(self), 'rrdTemplates', False)
                and getattr(aq_base(self.rrdTemplates),id,False)):
                self.rrdTemplates._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)

    def manage_exportRRDTemplates(self, ids=(), REQUEST=None):
        """Export RRDTemplates from this DeviceClass 
        (skips ones in other Classes)
        """
        if not ids:
            return self.callZenScreen(REQUEST)
        for id in ids:
            templates = getattr(aq_base(self), 'rrdTemplates')
            obj = getattr(aq_base(self.rrdTemplates), id)
            if templates and obj:
                self.zmanage_exportObject(obj, REQUEST)
        if REQUEST:
            return self.callZenScreen(REQUEST)

    security.declareProtected('Add DMD Objects', 'manage_importRRDTemplates')
    def manage_importRRDTemplates(self, REQUEST=None):
        """Import one or more RRD Templates.
        """
        return self.zmanage_importObjects(self.rrdTemplates, REQUEST)


    def createCatalog(self):
        """make the catalog for device searching
        """
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # Make catalog for Devices
        manage_addZCatalog(self, self.default_catalog,
            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        cat.addIndex('id', makeFieldIndex('id'))
        cat.addIndex('summary', makeFieldIndex('summary'))
        zcat.addColumn('getPrimaryId')
    
        # make catalog for device components
        manage_addZCatalog(self, "componentSearch", "componentSearch")
        zcat = self._getOb("componentSearch")
        cat = zcat._catalog
        cat.addIndex('meta_type', makeFieldIndex('meta_type'))
        # XXX still using regular FieldIndex here for now, since this contains
        # binary information
        zcat.addIndex('monitored', 'FieldIndex')
        zcat.addColumn('getPrimaryId')
        

    def reIndex(self):
        """Go through all devices in this tree and reindex them."""
        zcat = self._getOb(self.default_catalog)
        zcat.manage_catalogClear()
        transaction.savepoint()
        for dev in self.getSubDevicesGen():
            dev.index_object()
            for comp in dev.getDeviceComponents():
                comp.index_object()
            transaction.savepoint()



    def buildDeviceTreeProperties(self):
        devs = self.getDmdRoot("Devices")
        if getattr(aq_base(devs), "zSnmpCommunities", False): return

        # map deviec class to python classs (seperate from device class name)
        devs._setProperty("zPythonClass", "")

        # production state threshold at which to start monitoring boxes
        devs._setProperty("zProdStateThreshold", 500, type="int")

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

        # RRD properties
        #FIXME - should this be added to allow for more flexability of
        # RRDTemplate binding?
        #devs._setProperty("zRRDTemplateName", "")
        
        # Ping monitor properties
        devs._setProperty("zPingInterfaceName", "")
        devs._setProperty("zPingInterfaceDescription", "")

        # Status monitor properites
        devs._setProperty("zSnmpMonitorIgnore", False, type="boolean")
        devs._setProperty("zPingMonitorIgnore", False, type="boolean")
        devs._setProperty("zWmiMonitorIgoner", False, type="boolean")
        devs._setProperty("zXmlRpcMonitorIgnore", False, type="boolean")

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

        # Device context Event Mapping
        #FIXME this is half baked needs to be specific to an event class
        #devs._setProperty("zEventSeverity", -1, type="int")

        # Windows WMI collector properties
        devs._setProperty("zWinUser", "")
        devs._setProperty("zWinPassword", "")
        #devs._setProperty("zWinServices", "")
        devs._setProperty("zWinEventlogMinSeverity", 2, type="int")
        devs._setProperty("zWinEventlog", False, type="boolean")
        
        devs._setProperty("zCommandPath", "/usr/local/nagios/libexec")


InitializeClass(DeviceClass)
