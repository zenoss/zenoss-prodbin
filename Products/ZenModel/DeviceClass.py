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

__doc__="""DeviceClass
The primary organizer of device objects, managing zProperties and
their acquisition.
"""

import types
import time
import transaction
import logging
log = logging.getLogger('zen.DeviceClass')

import DateTime
from Globals import DTMLFile
from Globals import InitializeClass
from Acquisition import aq_base, aq_chain
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions

from Products.AdvancedQuery import MatchGlob, Or, Eq
from Products.CMFCore.utils import getToolByName

from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenUtils.Search import makeCaseInsensitiveFieldIndex
from Products.ZenUtils.Search import makeCaseInsensitiveKeywordIndex
from Products.ZenUtils.Search import makePathIndex, makeMultiPathIndex
from Products.ZenUtils.Utils import importClass, zenPath
from Products.ZenWidgets import messaging

from Products.ZenUtils.FakeRequest import FakeRequest

import RRDTemplate
from DeviceOrganizer import DeviceOrganizer
from ZenPackable import ZenPackable
from TemplateContainer import TemplateContainer

_marker = "__MARKER___"

def manage_addDeviceClass(context, id, title = None, REQUEST = None):
    """make a device class"""
    dc = DeviceClass(id, title)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main')


addDeviceClass = DTMLFile('dtml/addDeviceClass',globals())


class DeviceClass(DeviceOrganizer, ZenPackable, TemplateContainer):
    """
    DeviceClass is a device organizer that manages the primary classification
    of device objects within the Zenoss system.  It manages properties
    that are inherited through acquisition that modify the behavior of
    many different sub systems within Zenoss.
    It also handles the creation of new devices in the system.
    """

    # Organizer configuration
    dmdRootName = "Devices"

    manageDeviceSearch = DTMLFile('dtml/manageDeviceSearch',globals())
    manageDeviceSearchResults = DTMLFile('dtml/manageDeviceSearchResults',
                                            globals())

    portal_type = meta_type = event_key = "DeviceClass"

    default_catalog = 'deviceSearch'

    _properties = DeviceOrganizer._properties + (
                    {'id':'devtypes', 'type':'lines', 'mode':'w'},
                   )

    _relations = DeviceOrganizer._relations + ZenPackable._relations + \
                TemplateContainer._relations + (
        ("devices", ToManyCont(ToOne,"Products.ZenModel.Device","deviceClass")),
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
                { 'name'          : 'Classes'
                , 'action'        : 'deviceOrganizerStatus'
                , 'permissions'   : ( permissions.view, )
                },
                { 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (  permissions.view, )
                },
                { 'name'          : 'zProperties'
                , 'action'        : 'zPropertyEdit'
                , 'permissions'   : (permissions.view,)
                },
                { 'name'          : 'Templates'
                , 'action'        : 'perfConfig'
                , 'permissions'   : ('Manage DMD',)
                },
            )
         },
        )

    security = ClassSecurityInfo()
    
    def getPeerDeviceClassNames(self, pyclass=None):
        """
        Return a list of all device paths that have the Python class pyclass

        @param pyclass: Python class (default is this class)
        @type pyclass: Python class
        @return: list of device paths
        @rtype: list of strings
        """
        dcnames = []
        if pyclass == None:
            pyclass = self.getPythonDeviceClass()
        dclass = self.getDmdRoot("Devices")
        for orgname in dclass.getOrganizerNames():
            org = dclass.getOrganizer(orgname)
            if pyclass == org.getPythonDeviceClass():
                dcnames.append(orgname)
        dcnames.sort(lambda a, b: cmp(a.lower(), b.lower()))
        return dcnames

    deviceMoveTargets = getPeerDeviceClassNames
    childMoveTargets = getPeerDeviceClassNames


    def createInstance(self, id):
        """
        Create an instance based on its location in the device tree
        walk up the primary aq path looking for a python instance class that
        matches the name of the closest node in the device tree.

        @param id: id in DMD path
        @type id: string
        @return: new device object
        @rtype: device object
        """
        pyClass = self.getPythonDeviceClass()
        dev = pyClass(id)
        self.devices._setObject(id, dev)
        return self.devices._getOb(id)

    
    def getPythonDeviceClass(self):
        """
        Return the Python class object to be used for device instances in this 
        device class.  This is done by walking up the aq_chain of a deviceclass 
        to find a node that has the same name as a Python class or has an 
        attribute named zPythonClass that matches a Python class.

        @return: device class
        @rtype: device class
        """
        from Device import Device
        cname = getattr(self, "zPythonClass", None)
        if cname:
            try:
                return importClass(cname)
            except ImportError:
                log.exception("Unable to import class " + cname)
        return Device
   

    def moveDevices(self, moveTarget, deviceNames=None, REQUEST=None):
        """
        Override default moveDevices because this is a contained relation.
        If the Python class bound to a DeviceClass is different we convert to
        the new Python class adding / removing relationships as needed.

        @param moveTarget: organizer in DMD path
        @type moveTarget: string
        @param deviceNames: devices to move
        @type deviceNames: list of stringa
        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        if not moveTarget or not deviceNames: return self()
        target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
        if type(deviceNames) == types.StringType: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.findDeviceExact(devname)
            if not dev: continue
            source = dev.deviceClass().primaryAq()
            if dev.__class__ != target.getPythonDeviceClass():
                import StringIO
                from Products.ZenRelations.ImportRM import NoLoginImportRM

                def switchClass(o, module, klass):
                    """
                    Create an XML string representing the module in a
                    new class.

                    @param o: file-type object
                    @type o: file-type object
                    @param module: location in DMD
                    @type module: string
                    @param klass: class name
                    @type klass: string
                    @return: XML representation of the class
                    @rtype: string
                    """
                    o.seek(0)
                    l = o.readline()
                    al = l[1:-2].split()
                    for i in range(len(al)):
                        if al[i].startswith('module'):
                            al[i] = "module='%s'" % module
                        elif al[i].startswith('class'):
                            al[i] = "class='%s'" % klass
                    nl = "<" + " ".join(al) + ">\n"
                    o.seek(0)
                    nf = ["<objects>", nl]
                    nf.extend(o.readlines()[1:])
                    nf.append('</objects>')
                    return StringIO.StringIO("".join(nf))

                def devExport(d, module, klass):
                    """
                    Create an XML string representing the device d
                    at the DMD location module of type klass.

                    @param module: location in DMD
                    @type module: string
                    @param klass: class name
                    @type klass: string
                    @return: XML representation of the class
                    @rtype: string
                    """
                    o = StringIO.StringIO()
                    d.exportXml(o)
                    return switchClass(o, module, klass) 

                def devImport(xmlfile):
                    """
                    Load a new device from a file.

                    @param xmlfile: file type object
                    @type xmlfile: file type object
                    """
                    im = NoLoginImportRM(target.devices)
                    im.loadObjectFromXML(xmlfile)

                module = target.zPythonClass
                if module: 
                    klass = target.zPythonClass.split('.')[-1]
                else:
                    module = 'Products.ZenModel.Device'
                    klass = 'Device'
                xmlfile = devExport(dev, module,klass)
                source.devices._delObject(devname)
                devImport(xmlfile)
            else:
                dev._operation = 1
                source.devices._delObject(devname)
                target.devices._setObject(devname, dev)
            dev = target.devices._getOb(devname)
            dev.setLastChange()
            dev.setAdminLocalRoles()
            dev.index_object()
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(title='Devices Moved',
                                   body="Devices were moved to %s." % moveTarget)
            REQUEST['message'] = "Devices moved to %s" % moveTarget
            if not isinstance(REQUEST, FakeRequest):
                REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())
            else:
                if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                    return REQUEST['message']
                else:
                    return self.callZenScreen(REQUEST)


    def removeDevices(self, deviceNames=None, deleteStatus=False, 
                    deleteHistory=False, deletePerf=False,REQUEST=None):
        """
        See IManageDevice overrides DeviceManagerBase.removeDevices
        """
        if not deviceNames: return self()
        if type(deviceNames) in types.StringTypes: deviceNames = (deviceNames,)
        for devname in deviceNames:
            dev = self.findDevice(devname)
            dev.deleteDevice(deleteStatus=deleteStatus, 
                        deleteHistory=deleteHistory, deletePerf=deletePerf)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Devices Deleted',
                "Devices were deleted: %s." % ', '.join(deviceNames)
            )
            if REQUEST.has_key('oneKeyValueSoInstanceIsntEmptyAndEvalToFalse'):
                return 'Devices were deleted: %s.' % ', '.join(deviceNames)
            else:
                return self.callZenScreen(REQUEST)


    security.declareProtected('View', 'getEventDeviceInfo')
    def getEventDeviceInfo(self):
        """
        getEventDeviceInfo() -> return the info for NcoEventPopulator
        """
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
        """
        Return list of (devname,user,passwd,url) for each device.
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
            devinfo.append((dev.id, str(user), str(passwd), sev, dev.absolute_url()))
        return starttime, devinfo
    
    
    def getWinServices(self):
        """
        Return a list of (devname, user, passwd, {'EvtSys':0,'Exchange':0}) 
        """
        svcinfo = []
        allsvcs = {}
        for s in self.getSubComponents("WinService"):
            svcs=allsvcs.setdefault(s.hostname(),{})
            name = s.name()
            if type(name) == type(u''):
                name = name.encode(s.zCollectorDecoding)
            svcs[name] = (s.getStatus(), s.getAqProperty('zFailSeverity'))
        for dev in self.getSubDevices():
            if not dev.monitorDevice(): continue
            if getattr(dev, 'zWmiMonitorIgnore', False): continue
            svcs = allsvcs.get(dev.getId(), {})
            if not svcs and not dev.zWinEventlog: continue
            user = getattr(dev,'zWinUser','')
            passwd = getattr(dev, 'zWinPassword', '')
            svcinfo.append((dev.id, str(user), str(passwd), svcs))
        return svcinfo


    security.declareProtected('View', 'searchDeviceSummary')
    def searchDeviceSummary(self, query):
        """
        Search device summary index and return device objects
        """
        if not query: return []
        zcatalog = self._getCatalog()
        if not zcatalog: return []
        results = zcatalog({'summary':query})
        return self._convertResultsToObj(results)


    security.declareProtected('View', 'searchInterfaces')
    def searchInterfaces(self, query):
        """
        Search interfaces index and return interface objects
        """
        if not query: return []
        zcatalog = getattr(self, 'interfaceSearch', None)
        if not zcatalog: return []
        results = zcatalog(query)
        return self._convertResultsToObj(results)


    def _convertResultsToObj(self, results):
        devices = []
        for brain in results:
            try:
                devobj = self.getObjByPath(brain.getPrimaryId)
                devices.append(devobj)
            except KeyError:
                log.warn("bad path '%s' in index" % brain.getPrimaryId)

        return devices

    def _findDevice(self, devicename):
        query = Or(MatchGlob('id', devicename), 
                   Eq('getDeviceIp', devicename))
        return self._getCatalog().evalAdvancedQuery(query)

    def findDevicePath(self, devicename):
        """
        Look up a device and return its path
        """
        ret = self._findDevice(devicename)
        if not ret: return ""
        return ret[0].getPrimaryId

    def findDevice(self, devicename):
        """
        Look up device in catalog and return it
        """
        ret = self._findDevice(devicename)
        if ret: return ret[0].getObject()

    def findDeviceExact(self, devicename):
        """
        Look up device in catalog and return it.  devicename
        must match device id exactly
        """
        for brains in self._getCatalog()(id=devicename):
            dev = brains.getObject()
            if dev.id == devicename:
                return dev

    def findDevicePingStatus(self, devicename):
        """
        look up device in catalog and return its pingStatus
        """
        dev = self.findDevice(devicename)
        if dev: return dev.getPingStatusNumber()

    
    def getSubComponents(self, meta_type="", monitored=True):
        """
        Return generator of components, by meta_type if specified
        """
        zcat = self.componentSearch
        res = zcat({'meta_type': meta_type, 'monitored': monitored})
        for b in res:
            try:
                c = self.getObjByPath(b.getPrimaryId)
                if self.checkRemotePerm("View", c):
                    yield c
            except KeyError:
                log.warn("bad path '%s' in index 'componentSearch'", 
                            b.getPrimaryId)


    security.declareProtected("ZenCommon", "getMonitoredComponents")
    def getMonitoredComponents(self):
        """
        Return monitored components for devices within this DeviceDeviceClass
        """
        return self.getSubComponents()


    security.declareProtected('View', 'getRRDTemplates')
    def getRRDTemplates(self, context=None):
        """
        Return the actual RRDTemplate instances.
        """
        templates = {}
        if not context: context = self
        mychain = aq_chain(context)
        mychain.reverse()
        for obj in mychain:
            try:
                templates.update(dict([(t.id, t) for t in obj.rrdTemplates()]))
            except AttributeError:
                pass
        return templates.values()


    def getAvailableTemplates(self):
        """
        Returns all available templates
        """
        def cmpTemplates(a, b):
            return cmp(a.id.lower(), b.id.lower())
        templates = self.getRRDTemplates()
        templates.sort(cmpTemplates)
        pdc = self.getPythonDeviceClass()
        return [ t for t in templates
            if issubclass(pdc, t.getTargetPythonClass()) ]


    def bindTemplates(self, ids=(), REQUEST=None):
        """
        This will bind available templates to the zDeviceTemplates
        """
        return self.setZenProperty('zDeviceTemplates', ids, REQUEST)

    def removeZDeviceTemplates(self, REQUEST=None):
        """
        Deletes the local zProperty, zDeviceTemplates
        """
        if self.getPrimaryPath()[-2:] == ('dmd', 'Devices'):
            self.setZenProperty('zDeviceTemplates', ['Device'])
        else:
            self.deleteZenProperty('zDeviceTemplates')
        messaging.IMessageSender(self).sendToBrowser(
            'Bindings Reset',
            'Template bindings for this class were reset.'
        )
        return self.callZenScreen(REQUEST)


    def getAllRRDTemplates(self, rrdts=None):
        """
        Return all RRDTemplates at this level and below in the object tree.
        If rrdts is provided then it must be a list of RRDTemplates which
        will be extended with the templates from here and returned.

        The original getAllRRDTemplates() method has been renamed
        getAllRRDTemplatesPainfully().  It walks the object tree looking
        for templates which is a very slow way of going about things.
        The newer RRDTemplate.YieldAllRRDTemplate() method uses the
        searchRRDTemplates catalog to speed things up dramatically.
        YieldAllRRDTemplates is smart enough to revert to 
        getAllRRDTemplatesPainfully if the catalog is not present.

        The searchRRDTemplates catalog was added in 2.2
        """
        if rrdts == None:
            rrdts = []
        rrdts.extend(RRDTemplate.YieldAllRRDTemplates(self))
        return rrdts


    def getAllRRDTemplatesPainfully(self, rrdts=None):
        """
        RRDTemplate.YieldAllRRDTemplates() is probably what you want.
        It takes advantage of the searchRRDTemplates catalog to get
        much better performance.  This method iterates over objects looking
        for templates which is a slow, painful process.
        """
        if rrdts is None: rrdts = []
        rrdts.extend(self.rrdTemplates())
        for dev in self.devices():
            rrdts += dev.objectValues('RRDTemplate')
            for comps in dev.getDeviceComponents():
                rrdts += comps.objectValues('RRDTemplate')
        for child in self.children():
            child.getAllRRDTemplatesPainfully(rrdts)
        return rrdts


    security.declareProtected('Add DMD Objects', 'manage_addRRDTemplate')
    def manage_addRRDTemplate(self, id, REQUEST=None):
        """
        Add an RRDTemplate to this DeviceClass.
        """
        if not id: return self.callZenScreen(REQUEST)
        id = self.prepId(id)
        org = RRDTemplate.RRDTemplate(id)
        self.rrdTemplates._setObject(org.id, org)
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Template Added',
                'The "%s" template has been created.' % id
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_copyRRDTemplates')
    def manage_copyRRDTemplates(self, ids=(), REQUEST=None):
        """
        Put a reference to the objects named in ids in the clip board
        """
        if not ids: return self.callZenScreen(REQUEST)
        ids = [ id for id in ids if self.rrdTemplates._getOb(id, None) != None]
        if not ids: return self.callZenScreen(REQUEST)
        cp = self.rrdTemplates.manage_copyObjects(ids)
        if REQUEST:
            resp=REQUEST['RESPONSE']
            resp.setCookie('__cp', cp, path='/zport/dmd')
            REQUEST['__cp'] = cp
            messaging.IMessageSender(self).sendToBrowser(
                'Templates Copied',
                'Templates have been copied: %s' % ', '.join(ids)
            )
            return self.callZenScreen(REQUEST)
        return cp


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_pasteRRDTemplates')
    def manage_pasteRRDTemplates(self, moveTarget=None, cb_copy_data=None, REQUEST=None):
        """
        Paste RRDTemplates that have been copied before.
        """
        cp = None
        if cb_copy_data: cp = cb_copy_data
        elif REQUEST:
            cp = REQUEST.get("__cp",None)

        if cp:
            if moveTarget:
                target = self.getDmdRoot(self.dmdRootName).getOrganizer(moveTarget)
            else:
                target = self
            target.rrdTemplates.manage_pasteObjects(cp)
        else:
            target = None

        if REQUEST:
            REQUEST['RESPONSE'].setCookie('__cp', 'deleted', path='/zport/dmd',
                            expires='Wed, 31-Dec-97 23:59:59 GMT')
            REQUEST['__cp'] = None
            if target:
                message = "Template(s) moved to %s" % moveTarget
            else:
                message = None
            messaging.IMessageSender(self).sendToBrowser(
                'Templates Moved',
                message
            )
            if not isinstance(REQUEST, FakeRequest):
                url = target.getPrimaryUrlPath() + '/perfConfig'
                if message:
                    url += '?message=%s' % message
                REQUEST['RESPONSE'].redirect(url)
            else:
                return self.callZenScreen(REQUEST)


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_copyAndPasteRRDTemplates')
    def manage_copyAndPasteRRDTemplates(self, ids=(), copyTarget=None, REQUEST=None):
        """
        Copy the selected templates into the specified device class.
        """
        if not ids:
            messaging.IMessageSender(self).sendToBrowser(
                'Invalid',
                'No templates were selected.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)
        if copyTarget is None:
            messaging.IMessageSender(self).sendToBrowser(
                'Invalid',
                'No target was selected.',
                priority=messaging.WARNING
            )
            return self.callZenScreen(REQUEST)
        cp = self.manage_copyRRDTemplates(ids)
        return self.manage_pasteRRDTemplates(copyTarget, cp, REQUEST)


    security.declareProtected(ZEN_EDIT_LOCAL_TEMPLATES,
                              'manage_deleteRRDTemplates')
    def manage_deleteRRDTemplates(self, ids=(), paths=(), REQUEST=None):
        """
        Delete RRDTemplates from this DeviceClass 
        (skips ones in other Classes)
        """
        if not ids and not paths:
            return self.callZenScreen(REQUEST)
        for id in ids:
            if (getattr(aq_base(self), 'rrdTemplates', False)
                and getattr(aq_base(self.rrdTemplates),id,False)):
                self.rrdTemplates._delObject(id)
        for path in paths:
            temp = self.dmd.getObjByPath(path)
            if temp.deviceClass():
                temp.deviceClass().rrdTemplates._delObject(temp.id)
            else:
                temp.device()._delObject(temp.id)
        if REQUEST: 
            messaging.IMessageSender(self).sendToBrowser(
                'Templates Deleted',
                'Templates were deleted: %s' % ", ".join(ids)
            )
            return self.callZenScreen(REQUEST)


    def createCatalog(self):
        """
        Make the catalog for device searching
        """
        from Products.ZCatalog.ZCatalog import manage_addZCatalog

        # Make catalog for Devices
        manage_addZCatalog(self, self.default_catalog,
            self.default_catalog)
        zcat = self._getOb(self.default_catalog)
        cat = zcat._catalog
        for idxname in ['id',
            'getDeviceIp','getDeviceClassPath','getProdState']:
            cat.addIndex(idxname, makeCaseInsensitiveFieldIndex(idxname))
        cat.addIndex('getPhysicalPath', makePathIndex('getPhysicalPath'))
        cat.addIndex('path', makeMultiPathIndex('path'))
        zcat.addColumn('getPrimaryId')
        zcat.addColumn('id')
        zcat.addColumn('path')

        # make catalog for device components
        manage_addZCatalog(self, "componentSearch", "componentSearch")
        zcat = self._getOb("componentSearch")
        cat = zcat._catalog
        cat.addIndex('meta_type', makeCaseInsensitiveFieldIndex('meta_type'))
        cat.addIndex('getParentDeviceName',
            makeCaseInsensitiveFieldIndex('getParentDeviceName'))
        cat.addIndex('getCollectors',
            makeCaseInsensitiveKeywordIndex('getCollectors'))
        # XXX still using regular FieldIndex here for now, since this contains
        # binary information
        zcat.addIndex('monitored', 'FieldIndex')
        zcat.addColumn('getPrimaryId')
        zcat.addColumn('meta_type')


    def reIndex(self):
        """
        Go through all devices in this tree and reindex them.
        """
        zcat = getToolByName(self, self.default_catalog)
        zcat.manage_catalogClear()
        self.componentSearch.manage_catalogClear()
        transaction.savepoint()
        for dev in self.getSubDevicesGen_recursive():
            dev.index_object()
            for comp in dev.getDeviceComponentsNoIndexGen():
                comp.index_object()
            transaction.savepoint()


    def buildDeviceTreeProperties(self):
        """
        Create a new device tree with a default configuration
        """
        devs = self.getDmdRoot("Devices")
        if getattr(aq_base(devs), "zSnmpCommunities", False): return

        # map deviec class to python classs (seperate from device class name)
        devs._setProperty("zPythonClass", "")

        # production state threshold at which to start monitoring boxes
        devs._setProperty("zProdStateThreshold", 300, type="int")

        # Display the ifdescripion field or not
        devs._setProperty("zIfDescription", False, type="boolean")

        # Snmp collection properties
        devs._setProperty("zSnmpCommunities",["public", "private"],type="lines")
        devs._setProperty("zSnmpCommunity", "public")
        devs._setProperty("zSnmpPort", 161, type="int")
        devs._setProperty("zSnmpVer", "v1")
        devs._setProperty("zSnmpTries", 2, type="int")
        devs._setProperty("zSnmpTimeout", 2.5, type="float")
        devs._setProperty("zSnmpSecurityName", "")
        devs._setProperty("zSnmpAuthPassword", "")
        devs._setProperty("zSnmpPrivPassword", "")
        devs._setProperty("zSnmpAuthType", "")
        devs._setProperty("zSnmpPrivType", "")
        devs._setProperty("zRouteMapCollectOnlyLocal", False, type="boolean")
        devs._setProperty("zRouteMapCollectOnlyIndirect", False, type="boolean")
        devs._setProperty("zRouteMapMaxRoutes", 500, type="int")
        devs._setProperty("zInterfaceMapIgnoreTypes", "")
        devs._setProperty("zInterfaceMapIgnoreNames", "")
        devs._setProperty("zFileSystemMapIgnoreTypes", [], type="lines")
        devs._setProperty("zFileSystemMapIgnoreNames", "")
        devs._setProperty("zFileSystemSizeOffset", 1.0, type="float")
        devs._setProperty("zHardDiskMapMatch", "")
        devs._setProperty("zSysedgeDiskMapIgnoreNames", "")
        devs._setProperty("zIpServiceMapMaxPort", 1024, type="int")
        devs._setProperty("zDeviceTemplates", ["Device"], type="lines")
        devs._setProperty("zLocalIpAddresses", "^127|^0\.0|^169\.254|^224")
        devs._setProperty("zLocalInterfaceNames", "^lo|^vmnet")


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
        devs._setProperty("zWmiMonitorIgnore", True, type="boolean")
        devs._setProperty("zStatusConnectTimeout", 15.0, type="float")

        # DataCollector properties
        devs._setProperty("zCollectorPlugins", [], type='lines')
        devs._setProperty("zCollectorClientTimeout", 180, type="int")
        devs._setProperty("zCollectorDecoding", 'latin-1')
        devs._setProperty("zCommandUsername", "")
        devs._setProperty("zCommandPassword", "")
        devs._setProperty("zCommandProtocol", "ssh")
        devs._setProperty("zCommandPort", 22, type="int")
        devs._setProperty("zCommandLoginTries", 1, type="int")
        devs._setProperty("zCommandLoginTimeout", 10.0, type="float")
        devs._setProperty("zCommandCommandTimeout", 10.0, type="float")
        devs._setProperty("zCommandSearchPath", [], type="lines")
        devs._setProperty("zCommandExistanceTest", "test -f %s")
        devs._setProperty("zCommandPath", zenPath("libexec"))
        devs._setProperty("zTelnetLoginRegex", "ogin:.$")
        devs._setProperty("zTelnetPasswordRegex", "assword:")
        devs._setProperty("zTelnetSuccessRegexList",
                            ['\$.$', '\#.$'], type="lines")
        devs._setProperty("zTelnetEnable", False, type="boolean")
        devs._setProperty("zTelnetEnableRegex", "assword:")
        devs._setProperty("zTelnetTermLength", True, type="boolean")
        devs._setProperty("zTelnetPromptTimeout", 10.0, type="float")
        devs._setProperty("zKeyPath", "~/.ssh/id_dsa")
        devs._setProperty("zMaxOIDPerRequest", 40, type="int")

        # Extra stuff for users
        devs._setProperty("zLinks", "")

        # Device context Event Mapping
        #FIXME this is half baked needs to be specific to an event class
        #devs._setProperty("zEventSeverity", -1, type="int")

        # Windows WMI collector properties
        devs._setProperty("zWinUser", "")
        devs._setProperty("zWinPassword", "")
        devs._setProperty("zWinEventlogMinSeverity", 2, type="int")
        devs._setProperty("zWinEventlog", False, type="boolean")

        # Icon path
        devs._setProperty("zIcon", "/zport/dmd/img/icons/noicon.png")


    def zenPropertyOptions(self, propname):
        """
        Provide a set of default options for a zProperty

        @param propname: zProperty name
        @type propname: string
        @return: list of zProperty options
        @rtype: list
        """
        if propname == 'zCollectorPlugins':
            from Products.DataCollector.Plugins import loadPlugins
            names = [ldr.pluginName() for ldr in loadPlugins(self.dmd)]
            names.sort()
            return names
        if propname == 'zCommandProtocol':
            return ['ssh', 'telnet']
        if propname == 'zSnmpVer':
            return ['v1', 'v2c', 'v3']
        if propname == 'zSnmpAuthType':
            return ['', 'MD5', 'SHA']
        if propname == 'zSnmpPrivType':
            return ['', 'DES', 'AES']
        return DeviceOrganizer.zenPropertyOptions(self, propname)


    def pushConfig(self, REQUEST=None):
        """
        This will result in a push of all the devices to live collectors

        @param REQUEST: Zope REQUEST object
        @type REQUEST: Zope REQUEST object
        """
        self._p_changed = True
        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Pushed Changes',
                'Changes to %s were pushed to collectors.' % self.id
            )
            return self.callZenScreen(REQUEST)


    security.declareProtected('Change Device', 'setLastChange')
    def setLastChange(self, value=None):
        """
        Set the changed datetime for this device.

        @param value: changed datetime. Default is now.
        @type value: number
        """
        if value is None:
            value = time.time()
        self._lastChange = float(value)

    def register_devtype(self, description, protocol):
        """
        Define this class in terms of a description of the devices it should
        contain and the protocol by which they would normally be monitored.
        """
        t = (description, protocol)
        if not self.hasProperty('devtypes'):
            self._setProperty('devtypes', [], 'lines')
        if t not in self.devtypes:
            self.devtypes.append(t)
            self._p_changed = True

    def unregister_devtype(self, description, protocol):
        t = (description, protocol)
        if self.hasProperty('devtypes'):
            if t in self.devtypes:
                self.devtypes.remove(t)
                self._p_changed = True


InitializeClass(DeviceClass)
