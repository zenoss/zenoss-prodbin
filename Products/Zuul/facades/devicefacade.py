##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009-2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import socket
import re
import os
import logging
import subprocess
from itertools import imap
from ZODB.transact import transact
from zope.interface import implements
from zope.event import notify
from zope.component import getMultiAdapter
from Products.AdvancedQuery import Eq, Or, Generic, And
from Products.Zuul.decorators import info
from Products.Zuul.utils import unbrain
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IDeviceFacade, ICatalogTool, IInfo, ITemplateNode, IMetricServiceGraphDefinition
from Products.Jobber.facade import FacadeMethodJob
from Products.Jobber.jobs import SubprocessJob
from Products.Zuul.tree import SearchResults
from Products.DataCollector.Plugins import CoreImporter, PackImporter, loadPlugins
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.ComponentGroup import ComponentGroup
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.System import System
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Device import Device
from Products.ZenMessaging.ChangeEvents.events import ObjectAddedToOrganizerEvent, \
    ObjectRemovedFromOrganizerEvent
from Products.Zuul import getFacade
from Products.Zuul.exceptions import DatapointNameConfict
from Products.Zuul.utils import ZuulMessageFactory as _t, UncataloguedObjectException
from Products.Zuul.interfaces import IDeviceCollectorChangeEvent
from Products.Zuul.catalog.events import IndexingEvent
from Products.ZenUtils.IpUtil import isip, getHostByName
from Products.ZenUtils.Utils import getObjectsFromCatalog
from Products.ZenEvents.Event import Event
from Products.ZenUtils.Utils import binPath, zenPath
from Acquisition import aq_base
from Products.Zuul.infos.metricserver import MultiContextMetricServiceGraphDefinition


iszprop = re.compile("z[A-Z]").match
log = logging.getLogger('zen.DeviceFacade')


class DeviceCollectorChangeEvent(object):
    implements(IDeviceCollectorChangeEvent)
    """
    Collector change event for device.
    """

    def __init__(self, context, collector, movedDevices, asynchronous):
        self._context = context
        self._collector = collector
        self._movedDevices = movedDevices
        self._asynchronous = asynchronous
        self.jobs = []

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
    def asynchronous(self):
        return self._asynchronous


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
        notify(IndexingEvent(obj))

    def findComponentIndex(self, componentUid, uid=None, meta_type=None,
                           sort='name', dir='ASC', name=None):
        comps = self._componentSearch(uid=uid, meta_type=meta_type, sort=sort,
                                       dir=dir, name=name)
        for i, b in enumerate(comps):
            if '/'.join(b._object.getPrimaryPath())==componentUid:
                return i

    def _filterComponents(self, comps, keys, query):
        """
        Returns a list of components where one of the attributes in keys contains
        the query (case-insensitive).

        @type  comps: SearchResults
        @param comps: All the Components for this query
        @type  keys: List
        @param keys: List of strings of fields that we are filtering on
        @type  query: String
        @param query: Search Term
        @rtype:   List
        @return:  List of Component Info objects that match the query
        """
        results = []
        query = query.lower()
        for comp in comps:
            keep = False
            for key in keys:
                # non searchable fields
                if key in ('uid', 'uuid', 'events', 'status', 'severity'):
                    continue
                val = getattr(comp, key, None)
                if not val:
                    continue
                if callable(val):
                    val = val()
                if IInfo.providedBy(val):
                    val = val.name
                if query in str(val).lower():
                    keep = True
                    break
            if keep:
                results.append(comp)
        return results

    def _componentSearch(self, uid=None, types=(), meta_type=(), start=0,
                         limit=None, sort='name', dir='ASC', name=None, keys=()):
        reverse = dir=='DESC'
        if isinstance(types, basestring):
            types = (types,)
        if isinstance(meta_type, basestring):
            meta_type = (meta_type,)
        querySet = []
        if meta_type:
            querySet.append(Or(*(Eq('meta_type', t) for t in meta_type)))
        querySet.append(Generic('getAllPaths', uid))
        query = And(*querySet)
        obj = self._getObject(uid)

        cat = obj.device().componentSearch
        if 'getAllPaths' not in cat.indexes():
            obj.device()._createComponentSearchPathIndex()
        brains = cat.evalAdvancedQuery(query)

        # unbrain the results
        comps=map(IInfo, map(unbrain, brains))


        # filter the components
        if name is not None:
            comps = self._filterComponents(comps, keys, name)

        total = len(comps)
        hash_ = str(total)

        def componentSortKey(parent):
            val = getattr(parent, sort)
            if val:
                if isinstance(val, list):
                    val = val[0]
                if callable(val):
                    val = val()
                if IInfo.providedBy(val):
                    val = val.name
            # Pad numeric values with 0's so that sort is
            # both alphabetically and numerically correct.
            # eth1/1  will sort on eth0000000001/0000000001
            # eth1/12 will sort on eth0000000001/0000000012
            return re.sub("[\d]+", lambda x:str.zfill(x.group(0),10), val) 

        # sort the components
        sortedResults = list(sorted(comps, key=componentSortKey, reverse=reverse))

        # limit the search results to the specified range
        if limit is None:
            pagedResult = sortedResults[start:]
        else:
            pagedResult = sortedResults[start:start + limit]

        # fetch any rrd data necessary
        self.bulkLoadMetricData(pagedResult)

        return SearchResults(iter(pagedResult), total, hash_, False)

    def getComponents(self, uid=None, types=(), meta_type=(), start=0,
                      limit=None, sort='name', dir='ASC', name=None, keys=()):
        return self._componentSearch(uid, types, meta_type, start, limit,
                                       sort, dir, name=name, keys=keys)

    def bulkLoadMetricData(self, infos):
        """
        If the info objects have the attribute dataPointsToFetch we
        will load all the datapoints in one metric service query
        instead of one per info object
        """
        if len(infos) == 0:
            return
        datapoints = set()
        indexedInfos = dict()
        for info in infos:
            indexedInfos[info._object.getResourceKey()] = info
            if hasattr(info, "dataPointsToFetch"):
                [datapoints.add(dp) for dp in info.dataPointsToFetch]

        # in case no metrics were asked for
        if len(datapoints) == 0:
            return
        # get the metric facade
        mfacade = getFacade('metric', self._dmd)
        # metric facade expects zenmodel objects or uids
        results = mfacade.getMultiValues([i._object for i in infos], datapoints, returnSet="LAST")

        # assign the metrics to the info objects
        for resourceKey, record in results.iteritems():
            if indexedInfos.get(resourceKey) is not None:
                info = indexedInfos[resourceKey]
                for key, val in record.iteritems():
                    info.setBulkLoadProperty(key, val)

    def getComponentTree(self, uid):
        from Products.ZenEvents.EventManagerBase import EventManagerBase
        componentTypes = {}
        uuidMap = {}

        dev = self._getObject(uid)
        for brain in dev.componentSearch():
            uuidMap[brain.getUUID] = brain.meta_type
            compType = componentTypes.setdefault(brain.meta_type, { 'count' : 0, 'severity' : 0 })
            compType['count'] += 1

        # Do one big lookup of component events and merge back in to type later
        if not uuidMap:
            return []

        zep = getFacade('zep')
        showSeverityIcon = self.context.dmd.UserInterfaceSettings.getInterfaceSettings().get('showEventSeverityIcons')
        if showSeverityIcon:
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

    def getDeviceUids(self, uid):
        cat = ICatalogTool(self._getObject(uid))
        return [b.getPath() for b in cat.search('Products.ZenModel.Device.Device')]

    def deleteComponents(self, uids):
        comps = imap(self._getObject, uids)
        for comp in comps:
            if comp.isLockedFromDeletion():
                raise Exception("Component %s is locked from deletion" % comp.id)

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
                parent = dev.getPrimaryParent()
                dev.deleteDevice(deleteStatus=deleteEvents,
                                 deletePerf=deletePerf)
                # Make absolutely sure that the count gets updated
                # when we delete a device.
                parent = self._dmd.unrestrictedTraverse("/".join(parent.getPhysicalPath()))
                parent.setCount()
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

    def deleteDevices(self, uids, deleteEvents=False, deletePerf=True):
        """
        Return a list of device uids underneath an organizer. This includes
        all the devices belonging to an child organizers.
        """
        devs = imap(self._getObject, uids)
        for dev in devs:
            if dev.isLockedFromDeletion():
                raise Exception("Device %s is locked from deletion" % dev.id)

        return self._deleteDevices(uids, deleteEvents, deletePerf)

    @info
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

    def setProductionState(self, uids, state, asynchronous=False):
        if asynchronous:
            self._dmd.JobManager.addJob(
                FacadeMethodJob,
                description="Set state %s for %s" % (state, ','.join(uids)),
                kwargs=dict(
                    facadefqdn="Products.Zuul.facades.devicefacade.DeviceFacade",
                    method="_setProductionState",
                    uids=uids,
                    state=state
                ))
        else:
            self._setProductionState(uids, state)

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
            # update the componentSearch catalog
            comp.index_object(idxs=('monitored',))

            # update the global catalog as well
            notify(IndexingEvent(comp, idxs=('monitored',)))

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

    def _setProductionState(self, uids, state):
        if isinstance(uids, basestring):
            uids = (uids,)
        for uid in uids:
            dev = self._getObject(uid)
            if isinstance(dev, Device):
                dev.setProdState(int(state))

    @info
    def moveDevices(self, uids, target, asynchronous=True):
        if asynchronous:
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
        else:
            return self._moveDevices(uids, target)

    def getDeviceByIpAddress(self, deviceName, collector="localhost", ipAddress=""):
        # convert device name to an ip address
        if not ipAddress:
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

    @info
    def setCollector(self, uids, collector, moveData=False, asynchronous=True):
        # Keep 'moveData' in signature even though it's unused now
        if asynchronous:
            prettyUids = ", ".join([uid.split('/')[-1] for uid in uids])
            return self._dmd.JobManager.addJob(
                FacadeMethodJob, description="Move devices %s to collector %s" % (prettyUids, collector),
                kwargs=dict(
                    facadefqdn="Products.Zuul.facades.devicefacade.DeviceFacade",
                    method="_setCollector",
                    uids=uids,
                    collector=collector
                ))
        else:
            return self._setCollector(uids, collector)

    def _setCollector(self, uids, collector, moveData=False, asynchronous=True):
        movedDevices = []
        for uid in uids:
            info = self.getInfo(uid)
            movedDevices.append({
                'id': uid.split("/")[-1],
                'fromCollector': info.collector,
            })
            info.collector = collector

        # If an event is desired at this point, use a DeviceCollectorChangeEvent here

    @info
    def addDevice(self, deviceName, deviceClass, title=None, snmpCommunity="",
                  snmpPort=161, manageIp="", model=False, collector='localhost',
                  rackSlot=0, productionState=1000, comments="",
                  hwManufacturer="", hwProductName="", osManufacturer="",
                  osProductName="", priority = 3, tag="", serialNumber="",
                  locationPath="", zCommandUsername="", zCommandPassword="",
                  zWinUser="", zWinPassword="", systemPaths=[], groupPaths=[],
                  zProperties={}, cProperties={},
                  ):
        zProps = dict(zSnmpCommunity=snmpCommunity,
                      zSnmpPort=snmpPort,
                      zCommandUsername=zCommandUsername,
                      zWinUser=zWinUser,
                      zWinPassword=zWinPassword
                 )
        zProps.update(zProperties)
        model = model and "Auto" or "none"
        perfConf = self._dmd.Monitors.getPerformanceMonitor(collector)
        jobrecords = perfConf.addCreateDeviceJob(deviceName=deviceName,
                                               devicePath=deviceClass,
                                               performanceMonitor=collector,
                                               discoverProto=model,
                                               manageIp=manageIp,
                                               zProperties=zProps,
                                               cProperties=cProperties,
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
        return jobrecords

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
                yield template

    def setBoundTemplates(self, uid, templateIds):
        obj = self._getObject(uid)

        # check for datapoint name conflicts
        bound_dp_names = {}
        for template in obj.getAvailableTemplates():
            if template.id in templateIds:
                dp_names = set(template.getRRDDataPointNames())
                intersection = dp_names.intersection(bound_dp_names)
                if intersection:
                    dp_name = intersection.pop()
                    other_id = bound_dp_names[dp_name]
                    fmt = "both {template.id} and {other_id} have a datapoint named {dp_name}"
                    raise DatapointNameConfict(fmt.format(template=template, other_id=other_id, dp_name=dp_name))
                for dp_name in dp_names:
                    bound_dp_names[dp_name] = template.id

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
                except UncataloguedObjectException:
                    pass

    def addLocationOrganizer(self, contextUid, id, description = '', address=''):
        org = super(DeviceFacade, self).addOrganizer(contextUid, id, description)
        org.address = address
        return org

    def addDeviceClass(self, contextUid, id, description = '', connectionInfo=None):
        org = super(DeviceFacade, self).addOrganizer(contextUid, id, description)
        if connectionInfo:
            org.connectionInfo = connectionInfo
        return org

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
            pluginDocs = module.__doc__
            if pluginDocs:
                pluginDocs = '<pre>' + pluginDocs.replace('\n', '\n<br/>') + '</pre>'
            docs[plugin.pluginName] = pluginDocs
        return docs

    def getConnectionInfo(self, uid):
        obj = self._getObject(uid)
        result = []
        deviceClass = obj
        if not isinstance(obj, DeviceClass):
            deviceClass = obj.deviceClass()
        for prop in deviceClass.primaryAq().getZ('zCredentialsZProperties', []):
            result.append(obj.exportZProperty(prop))
        return result

    def getGraphDefs(self, uid, drange):
        obj = self._getObject(uid)
        graphs = []
        # getGraphObjects is expected to return a tuple of size 2.
        # The graph definition and the context for that graph
        # definition.
        if hasattr(obj, "getGraphObjects"):
            for graph, ctx in obj.getGraphObjects():
                info = getMultiAdapter((graph, ctx), IMetricServiceGraphDefinition)
                # if there is a separate context display that as the title
                if ctx != obj:
                    info._showContextTitle = True
                graphs.append(info)
        return graphs

    def addIpRouteEntry(self, uid, dest, routemask, nexthopid, interface,
                        routeproto, routetype, userCreated):
        device = self._getObject(uid)
        device.os.addIpRouteEntry(dest, routemask, nexthopid, interface,
                        routeproto, routetype, userCreated)

    def addIpInterface(self, uid, newId, userCreated):
        device = self._getObject(uid)
        device.os.addIpInterface(newId, userCreated)

    def addOSProcess(self, uid, newClassName, example, userCreated):
        device = self._getObject(uid)
        device.os.addOSProcess(newClassName, example, userCreated)

    def addFileSystem(self, uid, newId, userCreated):
        device = self._getObject(uid)
        device.os.addFileSystem(newId, userCreated)

    def addIpService(self, uid, newClassName, protocol, userCreated):
        device = self._getObject(uid)
        device.os.addIpService(newClassName, protocol, userCreated)

    def addWinService(self, uid, newClassName, userCreated):
        device = self._getObject(uid)
        device.os.addWinService(newClassName, userCreated)

    def getSoftware(self, uid):
        obj = self._getObject(uid)
        softwares = (IInfo(s) for s in obj.os.software.objectValuesGen())
        return softwares

    def getOverriddenObjectsList(self, uid, propname, relName='devices'):
        obj = self._getObject(uid)
        objects = []
        for inst in obj.getSubInstances(relName):
          if inst.isLocal(propname) and inst not in objects:
            objects.append( { 'devicelink':inst.getPrimaryDmdId(), 'props':getattr(inst, propname), 'proptype': inst.getPropertyType(propname) } )
        for inst in obj.getOverriddenObjects(propname):
          objects.append( { 'devicelink':inst.getPrimaryDmdId(), 'props':getattr(inst, propname), 'proptype': inst.getPropertyType(propname) } )
        return objects

    def getOverriddenObjectsParent(self, uid, propname=''):
        obj = self._getObject(uid)
        if propname == '':
            prop = ''
            proptype = ''
        else:
            prop = getattr(obj, propname)
            proptype = obj.getPropertyType(propname)
        return [{'devicelink':uid, 'props':prop, 'proptype':proptype}]

    def getOverriddenZprops(self, uid, all=True, pfilt=iszprop):
        """
        Return list of device tree property names.
        If all use list from property root node.
        """
        obj = self._getObject(uid)
        if all:
            rootnode = obj.getZenRootNode()
        else:
            if obj.id == obj.dmdRootName: return []
            rootnode = aq_base(obj)
        return sorted(prop for prop in rootnode.propertyIds() if pfilt(prop))

    def clearGeocodeCache(self):
        """
        This clears the geocode cache by reseting the latlong property of
        all locations.
        """
        results = ICatalogTool(self._dmd.Locations).search('Products.ZenModel.Location.Location')
        for brain in results:
            try:
                brain.getObject().latlong = None
            except:
                log.warn("Unable to clear the geocodecache from %s " % brain.getPath())

    @info
    def getGraphDefinitionsForComponent(self, uid):
        graphDefs = dict()
        obj = self._getObject(uid)
        if isinstance(obj, ComponentGroup):
            components = obj.getComponents()
        else:
            components = list(getObjectsFromCatalog(obj.componentSearch, None, log))

        for component in components:
            if graphDefs.get(component.meta_type):
                continue
            graphDefs[component.meta_type] = [graphDef.id for graphDef, _ in component.getGraphObjects()]
        return graphDefs

    def getComponentGraphs(self, uid, meta_type, graphId, allOnSame=False):
        obj = self._getObject(uid)

        # get the components we are rendering graphs for
        query = {}
        query['meta_type'] = meta_type
        if isinstance(obj, ComponentGroup):
            components = [comp for comp in obj.getComponents() if comp.meta_type == meta_type]
        else:
            components = list(getObjectsFromCatalog(obj.componentSearch, query, log))

        graphDef = None

        # get the graph def
        for comp in components:
            # find the first instance
            for graph, ctx in comp.getGraphObjects():
                if graph.id == graphId:
                    graphDef = graph
                    break
            if graphDef:
                break
        if not graphDef:
            return []

        if allOnSame:
            return [MultiContextMetricServiceGraphDefinition(graphDef, components)]

        graphs = []
        for comp in components:
            info = getMultiAdapter((graph, comp), IMetricServiceGraphDefinition)
            graphs.append(info)
        return graphs

    def getDevTypes(self, uid):
        """
        Returns a list of devtypes for use for the wizard
        """
        devtypes = []
        org = self._getObject(uid)
        subOrgs = org.getSubOrganizers()
        # include the top level organizers in the list of device types
        organizers = [org] + subOrgs
        for org in organizers:
            org_name = org.getOrganizerName()
            org_id = org.getPrimaryId()
            if not hasattr(aq_base(org), 'devtypes') or not org.devtypes:
                devtypes.append({
                    'value': org_id,
                    'description': org_name,
                    'protocol': "",
                })
                continue
            for t in org.devtypes:
                try:
                    desc, ptcl = t
                except ValueError:
                    continue

                # Both must be defined
                if not ptcl or not desc:
                    continue

                # special case for migrating from WMI to WinRM so we
                # can allow the zenpack to be backwards compatible
                # ZEN-19596:  Add support for Cluster and any sub-class for
                #             Windows and Cluster
                ms_dev_classes = ('/Server/Microsoft/{}'.format(cls)
                                  for cls in ('Windows', 'Cluster'))
                matched_org_to_dev_cls = any(org_name.startswith(cls)
                                             for cls in ms_dev_classes)
                if matched_org_to_dev_cls and ptcl == 'WMI':
                    ptcl = "WinRM"
                devtypes.append({
                    'value': org_id,
                    'description': desc,
                    'protocol': ptcl,
                })
        return sorted(devtypes, key=lambda x: x.get('description'))

