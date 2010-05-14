###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from itertools import imap
from zope.interface import implements
from Acquisition import aq_base
from zope.event import notify
from Products.AdvancedQuery import Eq, Or, And, MatchRegexp
from Products.Zuul.decorators import info
from Products.Zuul.utils import unbrain
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IDeviceFacade, ICatalogTool, IInfo, ITemplateNode, ILocationOrganizerInfo
from Products.Zuul.tree import SearchResults
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.System import System
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.Device import Device
from Products.Zuul import getFacade
from Products.Zuul.utils import ZuulMessageFactory as _t
from Products.Zuul.catalog.events import IndexingEvent


class DeviceFacade(TreeFacade):
    """
    Facade for device stuff.
    """
    implements(IDeviceFacade)

    @property
    def _classFactory(self):
        return DeviceClass

    @property
    def _root(self):
        return self._dmd.Devices

    @property
    def _instanceClass(self):
        return 'Products.ZenModel.Device.Device'

    def _parameterizedWhere(self, uid=None, where=None):
        # Override the default to avoid searching instances and just
        # look up the where clause for the thing itself
        zem = self._dmd.ZenEventManager
        if not where:
            ob = self._getObject(uid)
            where = zem.lookupManagedEntityWhere(ob)
        where = where.replace('%', '%%')
        return where, []

    def getEventSummary(self, uid=None, where=None):
        zem = self._dmd.ZenEventManager
        if where:
            pw = self._parameterizedWhere(where=where)
        else:
            pw = self._parameterizedWhere(uid)
        summary = zem.getEventSummary(parameterizedWhere=pw)
        severities = (c[0].lower() for c in zem.severityConversions)
        counts = (s[2] for s in summary)
        return zip(severities, counts)

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
        d = {}
        # Build a dictionary with device/component
        for b in self._componentSearch(uid, types, meta_type):
            component = b.id
            path = b.getPath().split('/')
            device = path[path.index('devices') + 1]
            d.setdefault(b.meta_type, []).append(dict(device=device,
                                                      component=component))
        # Get count, status per meta_type
        result = []
        for compType in d:
            # Number of components
            compCount = len(d[compType])
            # Severity counts
            where = []
            vals = []
            for criterion in d[compType]:
                s = []
                # criterion is a dict
                for k, v in criterion.iteritems():
                    s.append('%s=%%s' % k)
                    vals.append(v)
                crit = ' and '.join(s)
                where.append('(%s)' % crit)
            zem = self._dmd.ZenEventManager
            severities = (c[0].lower() for c in zem.severityConversions)
            if where:
                crit = ' or '.join(where)
                pw = ('(%s)' % crit, vals)
                summary = zem.getEventSummary(parameterizedWhere=pw)
                counts = (s[2] for s in summary)
            else:
                counts = [0]*5
            for sev, count in zip(severities, counts):
                if count:
                    break
            else:
                sev = 'clear'
            result.append({'type':compType, 'count':compCount, 'severity':sev})
        return result

    def deleteComponents(self, uids):
        comps = imap(self._getObject, uids)
        for comp in comps:
            comp.manage_deleteComponent()

    def deleteDevices(self, uids):
        devs = imap(self._getObject, uids)
        for dev in devs:
            dev.deleteDevice()

    def removeDevices(self, uids, organizer):
        # Resolve target if a path
        if isinstance(organizer, basestring):
            organizer = self._getObject(organizer)
        assert isinstance(organizer, DeviceOrganizer)
        organizername = organizer.getOrganizerName()
        devs = imap(self._getObject, uids)
        if isinstance(organizer, DeviceGroup):
            for dev in devs:
                names = dev.getDeviceGroupNames()
                try:
                    names.remove(organizername)
                except ValueError:
                    pass
                else:
                    dev.setGroups(names)
        if isinstance(organizer, System):
            for dev in devs:
                names = dev.getSystemNames()
                try:
                    names.remove(organizername)
                except ValueError:
                    pass
                else:
                    dev.setSystems(names)
        elif isinstance(organizer, Location):
            for dev in devs:
                dev.setLocation(None)

    @info
    def getUserCommands(self, uid=None):
        org = self._getObject(uid)
        return org.getUserCommands()

    def setProductInfo(self, uid, hwManufacturer=None, hwProductName=None,
                       osManufacturer=None, osProductName=None):
        dev = self._getObject(uid)
        dev.manage_editDevice(hwManufacturer=hwManufacturer,
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
                dev.productionState = state
                devids.append(dev.id)
                dev.index_object()
                notify(IndexingEvent(dev, ('productionState',), True))
        evfacade = getFacade('event', self._dmd)
        evfacade.setProductionState(devids, state)

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

    def setMonitored(self, uids, monitored=False):
        comps = imap(self._getObject, uids)
        for comp in comps:
            IInfo(comp).monitored = monitored

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

    def moveDevices(self, uids, target):
        # Resolve target if a path
        if isinstance(target, basestring):
            target = self._getObject(target)
        assert isinstance(target, DeviceOrganizer)
        devs = (self._getObject(uid) for uid in uids)
        targetname = target.getOrganizerName()
        if isinstance(target, DeviceGroup):
            for dev in devs:
                paths = set(dev.getDeviceGroupNames())
                paths.add(targetname)
                dev.setGroups(list(paths))
        elif isinstance(target, System):
            for dev in devs:
                paths = set(dev.getSystemNames())
                paths.add(targetname)
                dev.setSystems(list(paths))
        elif isinstance(target, Location):
            for dev in devs:
                dev.setLocation(targetname)
        elif isinstance(target, DeviceClass):
            self._dmd.Devices.moveDevices(targetname,[dev.id for dev in devs])


    def addDevice(self, deviceName, deviceClass, title=None, snmpCommunity="",
                  snmpPort=161, model=False, collector='localhost',
                  rackSlot=0, productionState=1000, comments="",
                  hwManufacturer="", hwProductName="", osManufacturer="",
                  osProductName="", priority = 3, tag="", serialNumber=""):
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
                                               title=title)
        return jobStatus

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
                yield ITemplateNode(template)

    def addLocationOrganizer(self, contextUid, id, description = '', address=''):
        context = self._getObject(contextUid)
        organizer = aq_base(context).__class__(id, description, address)
        context._setObject(id, organizer)
        return ILocationOrganizerInfo(organizer)
