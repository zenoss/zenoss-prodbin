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
from Products.AdvancedQuery import Eq, Or
from Products.Zuul.decorators import info
from Products.Zuul.utils import unbrain
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IDeviceFacade, ICatalogTool
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.System import System
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceClass import DeviceClass


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
            ob = self._findObject(uid)
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
        counts = (s[1]+s[2] for s in summary)
        return zip(severities, counts)

    def _componentSearch(self, uid=None, types=(), meta_type=(), start=0,
                         limit=None, sort='name', dir='ASC'):
        reverse = dir=='DESC'
        if isinstance(types, basestring):
            types = (types,)
        defaults =['Products.ZenModel.OSComponent.OSComponent',
                   'Products.ZenModel.HWComponent.HWComponent']
        defaults.extend(types)
        if isinstance(meta_type, basestring):
            meta_type = (meta_type,)
        query = None
        if meta_type:
            query = Or(*(Eq('meta_type', t) for t in meta_type))
        cat = ICatalogTool(self._getObject(uid))
        brains = cat.search(defaults, query=query, start=start, limit=limit,
                            orderby=sort, reverse=reverse)
        return brains

    @info
    def getComponents(self, uid=None, types=(), meta_type=(), start=0,
                      limit=None, sort='name', dir='ASC'):
        return imap(unbrain, self._componentSearch(uid, types, meta_type,
                                                   start, limit, sort, dir))

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
            count = len(d[compType])
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
                counts = (s[1]+s[2] for s in summary)
            else:
                counts = [0]*5
            for sev, count in zip(severities, counts):
                if count:
                    break
            else:
                sev = 'clear'
            result.append({'type':compType, 'count':count, 'severity':sev})
        return result

    def deleteDevices(self, uids):
        devs = imap(self._findObject, uids)
        for dev in devs:
            dev.deleteDevice()

    def removeDevices(self, uids, organizer):
        # Resolve target if a path
        if isinstance(organizer, basestring):
            organizer = self._findObject(organizer)
        assert isinstance(organizer, DeviceOrganizer)
        organizername = organizer.getOrganizerName()
        devs = imap(self._findObject, uids)
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

    def setLockState(self, uids, deletion=False, updates=False,
                     sendEvent=False):
        devs = imap(self._findObject, uids)
        for dev in devs:
            if deletion or updates:
                if deletion:
                    dev.lockFromDeletion(sendEvent)
                if updates:
                    dev.lockFromUpdates(sendEvent)
            else:
                dev.unlock()

    def resetCommunityString(self, uid):
        dev = self._findObject(uid)
        dev.manage_snmpCommunity()

    def moveDevices(self, uids, target):
        # Resolve target if a path
        if isinstance(target, basestring):
            target = self._findObject(target)
        assert isinstance(target, DeviceOrganizer)
        devs = (self._findObject(uid) for uid in uids)
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

