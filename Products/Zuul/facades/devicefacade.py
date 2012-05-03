###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import socket
from itertools import imap
from ZODB.transact import transact
from zope.interface import implements
from Acquisition import aq_base
from zope.event import notify
from ZODB.POSException import POSKeyError
from Products.AdvancedQuery import Eq, Or, And, MatchRegexp, Between
from Products.Zuul.decorators import info
from Products.Zuul.utils import unbrain
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IDeviceFacade, ICatalogTool, IInfo, ITemplateNode, ILocationOrganizerInfo
from Products.Jobber.facade import FacadeMethodJob
from Products.Zuul.tree import SearchResults
from Products.DataCollector.Plugins import CoreImporter, PackImporter, loadPlugins
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.System import System
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Device import Device
from Products.ZenMessaging.ChangeEvents.events import ObjectAddedToOrganizerEvent, \
    ObjectRemovedFromOrganizerEvent
from Products.Zuul import getFacade
from Products.Zuul.tree import PermissionedCatalogTool
from Products.Zuul.utils import ZuulMessageFactory as _t, UncataloguedObjectException
from Products.Zuul.interfaces import IDeviceCollectorChangeEvent
from Products.Zuul.catalog.events import IndexingEvent
from Products.ZenUtils.IpUtil import numbip, checkip, IpAddressError, ensureIp, isip, getHostByName
from Products.ZenUtils.IpUtil import getSubnetBounds
from Products.ZenEvents.Event import Event
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier
from Products.ZenUtils.jsonutils import unjson


class DeviceCollectorChangeEvent(object):
    implements(IDeviceCollectorChangeEvent)
    """
    Collector change event for device.
    """

    def __init__(self, context, collector, movedDevices, moveData):
        self._context = context
        self._collector = collector
        self._movedDevices = movedDevices
        self._moveData = moveData

    @property
    def context(self):
        return self._context

    @property
    def collector(self):
        return self._collector

    @property
    def movedDevices(self):
        return self._movedDevices

    @property
    def moveData(self):
        return self._moveData


class DeviceFacade(TreeFacade):
    """
    Facade for device stuff.
    """
    implements(IDeviceFacade)

    def _classFactory(self, contextUid):
        return DeviceClass

    @property
    def _root(self):
        return self._dmd.Devices

    @property
    def _instanceClass(self):
        return 'Products.ZenModel.Device.Device'

    def setInfo(self, uid, data):
        """
        """
        super(DeviceFacade, self).setInfo(uid, data)
        obj = self._getObject(uid)
        if isinstance(obj, Device):
            obj.index_object()

    def findComponentIndex(self, componentUid, uid=None, meta_type=None,
                           sort='name', dir='ASC', name=None):
        brains = self._componentSearch(uid=uid, meta_type=meta_type, sort=sort,
                                       dir=dir, name=name)
        for i, b in enumerate(brains):
            if b.getPath()==componentUid:
                return i

    def _componentSearch(self, uid=None, types=(), meta_type=(), start=0,
                         limit=None, sort='name', dir='ASC', name=None):
        reverse = dir=='DESC'
        if isinstance(types, basestring):
            types = (types,)
        defaults =['Products.ZenModel.DeviceComponent.DeviceComponent']
        defaults.extend(types)
        if isinstance(meta_type, basestring):
            meta_type = (meta_type,)
        query = None
        if meta_type:
            query = Or(*(Eq('meta_type', t) for t in meta_type))
        if name:
            namequery = MatchRegexp('name', '(?i).*%s.*' % name)
            query = namequery if query is None else And(query, namequery)
        cat = ICatalogTool(self._getObject(uid))
        brains = cat.search(defaults, query=query, start=start, limit=limit,
                            orderby=sort, reverse=reverse)
        return brains

    def getComponents(self, uid=None, types=(), meta_type=(), start=0,
                      limit=None, sort='name', dir='ASC', name=None):
        brains = self._componentSearch(uid, types, meta_type, start, limit,
                                       sort, dir, name)
        wrapped = imap(IInfo, imap(unbrain, brains))
        return SearchResults(wrapped, brains.total, brains.hash_)

    def getComponentTree(self, uid=None, types=(), meta_type=()):
        from Products.ZenEvents.EventManagerBase import EventManagerBase
        componentTypes = {}
        uuidMap = {}

        # Build a dictionary with device/component
        for brain in self._componentSearch(uid, types, meta_type):
            uuidMap[brain.uuid] = brain.meta_type

            compType = componentTypes.setdefault(brain.meta_type, { 'count' : 0, 'severity' : 0 })
            compType['count'] += 1

        # Do one big lookup of component events and merge back in to type later
        if not uuidMap:
            return []
        zep = getFacade('zep')
        severities = zep.getWorstSeverity(uuidMap.keys())
        for uuid, sev in severities.iteritems():
            compType = componentTypes[uuidMap[uuid]]
            compType['severity'] = max(compType['severity'], sev)

        result = []
        for name, compType in componentTypes.iteritems():
            result.append({
                'type' : name,
                'count' : compType['count'],
                'severity' : EventManagerBase.severities.get(compType['severity'], 0).lower()
            })

        return result

    def deleteComponents(self, uids):
        comps = imap(self._getObject, uids)
        for comp in comps:
            if hasattr(comp, 'manage_deleteComponent'):
                comp.manage_deleteComponent()
            else:
                raise Exception("%s %s cannot be manually deleted" %
                            (getattr(comp,'meta_type','component'),comp.id))

    def _deleteDevices(self, uids, deleteEvents=False, deletePerf=True):
        @transact
        def dbDeleteDevices(uids):
            devs = imap(self._getObject, uids)
            deletedIds = []
            for dev in devs:
                devid = dev.getId()
                deletedIds.append(devid)
                dev.deleteDevice(deleteStatus=deleteEvents,
                                 deletePerf=deletePerf)
            return deletedIds

        def uidChunks(uids, chunksize=10):
            i = 0
            maxi = len(uids)
            while i < maxi:
                nexti = i+chunksize
                yield uids[i:nexti]
                i = nexti

        deletedIds = sum(map(dbDeleteDevices, uidChunks(uids)), [])
        for devid in deletedIds:
            self._dmd.ZenEventManager.sendEvent(Event(
                    summary='Deleted device: '+devid,
                    severity=2, #info
                    eventClass='/Change/Remove', #zEventAction=history
                    device=devid))

    @info
    def deleteDevices(self, uids, deleteEvents=False, deletePerf=True):
        devdesc = ("device %s" % uids[0].split('/')[-1] if len(uids)==1
                   else "%s devices" % len(uids))
        return self._dmd.JobManager.addJob(
            FacadeMethodJob, description="Delete %s" % devdesc,
            kwargs=dict(
                facadefqdn="Products.Zuul.facades.devicefacade.DeviceFacade",
                method="_deleteDevices",
                uids=uids,
                deleteEvents=deleteEvents,
                deletePerf=deletePerf
            ))

    def removeDevices(self, uids, organizer):
        # Resolve target if a path
        if isinstance(organizer, basestring):
            organizer = self._getObject(organizer)
        assert isinstance(organizer, DeviceOrganizer)
        devs = map(self._getObject, uids)
        removed = []
        if isinstance(organizer, DeviceGroup):
            for dev in devs:
                oldGroupNames = dev.getDeviceGroupNames()
                newGroupNames = self._removeOrganizer(organizer, list(oldGroupNames))
                if oldGroupNames != newGroupNames:
                    dev.setGroups(newGroupNames)
                    notify(ObjectRemovedFromOrganizerEvent(dev, organizer))
                    removed.append(dev)

        elif isinstance(organizer, System):
            for dev in devs:
                oldSystemNames = dev.getSystemNames()
                newSystemNames = self._removeOrganizer(organizer, list(oldSystemNames))
                if newSystemNames != oldSystemNames:
                    dev.setSystems(newSystemNames)
                    notify(ObjectRemovedFromOrganizerEvent(dev, organizer))
                    removed.append(dev)

        elif isinstance(organizer, Location):
            for dev in devs:
                dev.setLocation(None)
                notify(ObjectRemovedFromOrganizerEvent(dev, organizer))
                removed.append(dev)

        return removed

    def _removeOrganizer(self, organizer, items):
        organizerName = organizer.getOrganizerName()
        if organizerName in items:
            items.remove(organizerName)
        return items

    @info
    def getUserCommands(self, uid=None):
        org = self._getObject(uid)
        return org.getUserCommands()

    def setProductInfo(self, uid, hwManufacturer=None, hwProductName=None,
                       osManufacturer=None, osProductName=None):
        dev = self._getObject(uid)
        dev.setProductInfo(hwManufacturer=hwManufacturer,
                              hwProductName=hwProductName,
                              osManufacturer=osManufacturer,
                              osProductName=osProductName)

    def setProductionState(self, uids, state):
        devids = []
        if isinstance(uids, basestring):
            uids = (uids,)
        for uid in uids:
            dev = self._getObject(uid)
            if isinstance(dev, Device):
                dev.setProdState(int(state))
                devids.append(dev.id)

    def setLockState(self, uids, deletion=False, updates=False,
                     sendEvent=False):
        devs = imap(self._getObject, uids)
        for dev in devs:
            if deletion or updates:
                if deletion:
                    dev.lockFromDeletion(sendEvent)
                if updates:
                    dev.lockFromUpdates(sendEvent)
            else:
                dev.unlock()

    def setMonitor(self, uids, monitor=False):
        comps = imap(self._getObject, uids)
        for comp in comps:
            IInfo(comp).monitor = monitor
            self._root.componentSearch.catalog_object(comp, idxs=('monitored',))

    def pushChanges(self, uids):
        devs = imap(self._getObject, uids)
        for dev in devs:
            dev.pushConfig()

    def modelDevices(self, uids):
        devs = imap(self._getObject, uids)
        for dev in devs:
            dev.collectDevice(background=True)

    def resetCommunityString(self, uid):
        dev = self._getObject(uid)
        dev.manage_snmpCommunity()

    def renameDevice(self, uid, newId):
        dev = self._getObject(uid)
        # pass in the request for the audit
        return dev.renameDevice(newId, self.context.REQUEST)

    def _moveDevices(self, uids, target):
        # Resolve target if a path
        if isinstance(target, basestring):
            target = self._getObject(target)
        assert isinstance(target, DeviceOrganizer)
        devs = (self._getObject(uid) for uid in uids)
        targetname = target.getOrganizerName()
        exports = 0
        if isinstance(target, DeviceGroup):
            for dev in devs:
                paths = set(dev.getDeviceGroupNames())
                paths.add(targetname)
                dev.setGroups(list(paths))
                notify(ObjectAddedToOrganizerEvent(dev, target))
        elif isinstance(target, System):
            for dev in devs:
                paths = set(dev.getSystemNames())
                paths.add(targetname)
                dev.setSystems(list(paths))
                notify(ObjectAddedToOrganizerEvent(dev, target))
        elif isinstance(target, Location):
            for dev in devs:
                if dev.location():
                    notify(ObjectRemovedFromOrganizerEvent(dev, dev.location()))
                dev.setLocation(targetname)
                notify(ObjectAddedToOrganizerEvent(dev, target))
        elif isinstance(target, DeviceClass):
            exports = self._dmd.Devices.moveDevices(targetname,[dev.id for dev in devs])
        return exports

    @info
    def moveDevices(self, uids, target):
        devdesc = ("device %s" % uids[0].split('/')[-1] if len(uids)==1
                   else "%s devices" % len(uids))
        return self._dmd.JobManager.addJob(
            FacadeMethodJob, description="Move %s to %s" % (devdesc, target),
            kwargs=dict(
                facadefqdn="Products.Zuul.facades.devicefacade.DeviceFacade",
                method="_moveDevices",
                uids=uids,
                target=target
            ))

    def getDeviceByIpAddress(self, deviceName, collector="localhost"):
        # convert device name to an ip address
        ipAddress = None
        if isip(deviceName):
            ipAddress = deviceName
        else:
            try:
                ipAddress = getHostByName(deviceName)
            except socket.error:
                # look for duplicate name
                return self.context.Devices.findDeviceByIdExact(deviceName)

        # find a device with the same ip on the same collector
        query = Eq('getDeviceIp', ipAddress)
        cat = self.context.Devices.deviceSearch
        brains = cat.evalAdvancedQuery(query)
        for brain in brains:
            if brain.getObject().getPerformanceServerName() == collector:
                return brain.getObject()

    def setCollector(self, uids, collector, moveData=False):
        movedDevices = []
        for uid in uids:
            info = self.getInfo(uid)
            movedDevices.append({
                'id': uid.split("/")[-1],
                'fromCollector': info.collector,
            })
            info.collector = collector
            notify(IndexingEvent(info._object))

        notify(DeviceCollectorChangeEvent(self.context, collector, movedDevices, moveData))

    @info
    def addDevice(self, deviceName, deviceClass, title=None, snmpCommunity="",
                  snmpPort=161, model=False, collector='localhost',
                  rackSlot=0, productionState=1000, comments="",
                  hwManufacturer="", hwProductName="", osManufacturer="",
                  osProductName="", priority = 3, tag="", serialNumber="",
                  locationPath="", systemPaths=[], groupPaths=[]
                  ):
        zProps = dict(zSnmpCommunity=snmpCommunity,
                           zSnmpPort=snmpPort)
        model = model and "Auto" or "none"
        perfConf = self._dmd.Monitors.getPerformanceMonitor(collector)
        jobStatus = perfConf.addDeviceCreationJob(deviceName=deviceName,
                                               devicePath=deviceClass,
                                               performanceMonitor=collector,
                                               discoverProto=model,
                                               zProperties=zProps,
                                               rackSlot=rackSlot,
                                               productionState=productionState,
                                               comments=comments,
                                               hwManufacturer=hwManufacturer,
                                               hwProductName=hwProductName,
                                               osManufacturer=osManufacturer,
                                               osProductName=osProductName,
                                               priority=priority,
                                               tag=tag,
                                               serialNumber=serialNumber,
                                               locationPath=locationPath,
                                               systemPaths=systemPaths,
                                               groupPaths=groupPaths,
                                               title=title)
        return jobStatus

    def remodel(self, deviceUid):
        fake_request = {'CONTENT_TYPE': 'xml'}
        device = self._getObject(deviceUid)
        return device.getPerformanceServer().collectDevice(
            device, background=True, REQUEST=fake_request)

    def addLocalTemplate(self, deviceUid, templateId):
        """
        Adds a local template on the device specified by deviceUid
        @param string deviceUid: absolute path to a device
        @param string templateId: the Id of the new template
        """
        device = self._getObject(deviceUid)
        device.addLocalTemplate(templateId)

    def removeLocalTemplate(self, deviceUid, templateUid):
        """
        Removes a local definition of a template on a device
        @param string deviceUid: Absolute path to the device that has the template
        @param string templateUid: Absolute path to the template we wish to remove
        """
        device = self._getObject(deviceUid)
        template = self._getObject(templateUid)
        device.removeLocalRRDTemplate(template.id)

    def getTemplates(self, id):
        object = self._getObject(id)
        rrdTemplates = object.getRRDTemplates()

        # used to sort the templates
        def byTitleOrId(left, right):
            return cmp(left.titleOrId().lower(), right.titleOrId().lower())

        for rrdTemplate in sorted(rrdTemplates, byTitleOrId):
            uid = '/'.join(rrdTemplate.getPrimaryPath())
            # only show Bound Templates
            if rrdTemplate.id in object.zDeviceTemplates:
                path = rrdTemplate.getUIPath()

                # if defined directly on the device do not show the path
                if isinstance(object, Device) and object.titleOrId() in path:
                    path = _t('Locally Defined')
                yield {'id': uid,
                       'uid': uid,
                       'path': path,
                       'text': '%s (%s)' % (rrdTemplate.titleOrId(), path),
                       'leaf': True
                       }

    def getLocalTemplates(self, uid):
        """
        Returns a dictionary of every template defined on the device specified by the uid
        @param string uid: absolute path of a device
        @returns [Dict] All the templates defined on this device
        """
        return [template for template in self.getTemplates(uid) if template['path'] == _t('Locally Defined')]

    def getUnboundTemplates(self, uid):
        return self._getBoundTemplates(uid, False)

    def getBoundTemplates(self, uid):
        return self._getBoundTemplates(uid, True)

    def _getBoundTemplates(self, uid, isBound):
        obj = self._getObject(uid)
        for template in obj.getAvailableTemplates():
            if (template.id in obj.zDeviceTemplates) == isBound:
                yield  template

    def setBoundTemplates(self, uid, templateIds):
        obj = self._getObject(uid)
        obj.bindTemplates(templateIds)

    def resetBoundTemplates(self, uid):
        obj = self._getObject(uid)
        # make sure we have bound templates before we remove them
        if obj.hasProperty('zDeviceTemplates'):
            obj.removeZDeviceTemplates()

    def getOverridableTemplates(self, uid):
        """
        A template is overrideable at the device if it is bound to the device and
        we have not already overridden it.
        @param string uid: the unique id of a device
        @returns a list of all available templates for the given uid
        """
        obj = self._getObject(uid)
        templates = obj.getRRDTemplates()
        for template in templates:
            # see if the template is already overridden here
            if not obj.id in template.getPhysicalPath():
                try:
                    yield ITemplateNode(template)
                except UncataloguedObjectException, e:
                    pass

    def addLocationOrganizer(self, contextUid, id, description = '', address=''):
        org = super(DeviceFacade, self).addOrganizer(contextUid, id, description)
        org.address = address
        return org


    def setZenProperty(self, uid, zProperty, value):
        """
        Sets the value of the zProperty for this user.
        The value will be forced into the type, throwing
        an exception if it fails
        @type  uid: String
        @param uid: unique identifier of an object
        @type  zProperty: String
        @param zProperty: identifier of the property
        @type  value: Anything
        @param value: What you want the new value of the property to be
        """
        obj = self._getObject(uid)
        # make sure it is the correct type
        ztype = obj.getPropertyType(zProperty)
        if ztype == 'int':
            value = int(value)
        if ztype == 'float':
            value = float(value)
        if ztype == 'string':
            value = str(value)
        # do not save * as passwords
        if obj.zenPropIsPassword(zProperty) and value == obj.zenPropertyString(zProperty):
            return
        return obj.setZenProperty(zProperty, value)

    def getModelerPluginDocStrings(self, uid):
        """
        Returns a dictionary of documentation for modeler plugins, indexed
        by the plugin name.
        """
        obj = self._getObject(uid)
        plugins = loadPlugins(obj)
        docs = {}
        packImporter = PackImporter()
        coreImporter = CoreImporter()
        for plugin in plugins:
            try:
                module = coreImporter.importModule(plugin.package, plugin.modPath)
            except ImportError:
                try:
                    module = packImporter.importModule(plugin.package, plugin.modPath)
                except ImportError:
                    # unable to import skip over this one
                    continue
            docs[plugin.pluginName] = module.__doc__
        return docs

    def getZenProperties(self, uid, exclusionList=()):
        """
        Returns information about and the value of every zen property.

        @type  uid: string
        @param uid: unique identifier of an object
        @type  exclusionList: Collection
        @param exclusionList: List of zproperty ids that we do not wish to retrieve
        """
        obj = self._getObject(uid)
        return obj.exportZProperties(exclusionList)

    def deleteZenProperty(self, uid, zProperty):
        """
        Removes the local instance of the each property in properties. Note
        that the property will only be deleted if a hasProperty is true
        @type  uid: String
        @param uid: unique identifier of an object
        @type  properties: Array
        @param properties: list of zenproperty identifiers that we wish to delete
        """
        obj = self._getObject(uid)
        if obj.hasProperty(zProperty):
            prop = self.getZenProperty(uid, zProperty)
            if prop['path'] == '/':
                raise Exception('Unable to delete root definition of a zProperty')
            obj.deleteZenProperty(zProperty)

    def getZenProperty(self, uid, zProperty):
        """
        Returns information about a zproperty for a
        given context, including its value
        @rtype:   Dictionary
        @return:  B{Properties}:
             - path: (string) where the property is defined
             - type: (string) type of zproperty it is
             - options: (Array) available options for the zproperty
             - value (Array) value of the zproperty
             - valueAsString (string)
        """
        obj = self._getObject(uid)
        prop = dict(
            path = obj.zenPropertyPath(zProperty),
            options = obj.zenPropertyOptions(zProperty),
            type=obj.getPropertyType(zProperty),
            )

        if not obj.zenPropIsPassword(zProperty):
            prop['value'] = obj.getZ(zProperty)
            prop['valueAsString'] = obj.zenPropertyString(zProperty)
        return prop

    def getGraphDefs(self, uid, drange):
        obj = self._getObject(uid)
        return obj.getDefaultGraphDefs(drange)

    def addIpRouteEntry(self, uid, dest, routemask, nexthopid, interface,
                        routeproto, routetype, userCreated):
        device = self._getObject(uid)
        device.os.addIpRouteEntry(dest, routemask, nexthopid, interface,
                        routeproto, routetype, userCreated)

    def addIpInterface(self, uid, newId, userCreated):
        device = self._getObject(uid)
        device.os.addIpInterface(newId, userCreated)

    def addOSProcess(self, uid, newClassName, userCreated):
        device = self._getObject(uid)
        device.os.addOSProcess(newClassName, userCreated)

    def addFileSystem(self, uid, newId, userCreated):
        device = self._getObject(uid)
        device.os.addFileSystem(newId, userCreated)

    def addIpService(self, uid, newClassName, protocol, userCreated):
        device = self._getObject(uid)
        device.os.addIpService(newClassName, protocol, userCreated)

    def addWinService(self, uid, newClassName, userCreated):
        device = self._getObject(uid)
        device.os.addWinService(newClassName, userCreated)
