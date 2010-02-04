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
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.decorators import info
from Products.Zuul.tree import TreeNode
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IDeviceFacade, IDeviceOrganizerNode
from Products.Zuul.interfaces import IDeviceOrganizerInfo
from Products.Zuul.interfaces import IDeviceInfo, IDevice, ICatalogTool
from Products.Zuul.facades import InfoBase
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
from Products.ZenModel.DeviceGroup import DeviceGroup
from Products.ZenModel.System import System
from Products.ZenModel.Location import Location
from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenUtils import IpUtil
from Products.Zuul import getFacade

def _organizerWhere(uid):
    """
    Duplicating a little code in EventManagerBase so as to avoid pulling
    all the objects. When we fix the event system we can probably do away
    with this.
    """
    orgname = uid.lstrip('/zport/dmd')
    if orgname.startswith('Devices'):
        return "DeviceClass like '%s%%'" % orgname.lstrip('Devices')
    elif orgname.startswith('Groups'):
        return "DeviceGroups like '%%|%s%%'" % orgname.lstrip('Groups')
    elif orgname.startswith('Systems'):
        return "Systems like '%%|%s%%'" % orgname.lstrip('Systems')
    elif orgname.startswith('Locations'):
        return "Location like '%s%%'" % orgname.lstrip('Locations')


class DeviceOrganizerNode(TreeNode):
    implements(IDeviceOrganizerNode)
    adapts(DeviceOrganizer)

    uiProvider = 'hierarchy'

    @property
    def _evsummary(self):
        where = _organizerWhere(self.uid)
        return getFacade('device').getEventSummary(where=where)

    @property
    def children(self):
        cat = ICatalogTool(self._object)
        orgs = cat.search(DeviceOrganizer, paths=(self.uid,), depth=1)
        return imap(DeviceOrganizerNode, orgs)

    @property
    def text(self):
        cat = ICatalogTool(self._object)
        numInstances = cat.count('Products.ZenModel.Device.Device', self.uid)
        text = super(DeviceOrganizerNode, self).text
        return {
            'text': text,
            'count': numInstances,
            'description': 'devices'
        }

    # All nodes are potentially branches, just some have no children
    leaf = False


class DeviceInfo(InfoBase):
    implements(IDeviceInfo)
    adapts(IDevice)

    @property
    def device(self):
        return self._object.id

    def getDevice(self):
        return self.device

    @property
    def ipAddress(self):
        if self._object.manageIp:
            return IpUtil.ipToDecimal(self._object.manageIp)

    @property
    def productionState(self):
        return self._object.convertProdState(self._object.productionState)

    @property
    def events(self):
        manager = self._object.getEventManager()
        severities = (c[0].lower() for c in manager.severityConversions)
        counts = (s[1]+s[2] for s in self._object.getEventSummary())
        return dict(zip(severities, counts))

    @property
    def availability(self):
        return self._object.availability().availability


class DeviceOrganizerInfo(InfoBase):
    implements(IDeviceOrganizerInfo)
    adapts(DeviceOrganizer)
    @property
    def events(self):
        mgr = self._object.getEventManager()
        sevs = (c[0].lower() for c in mgr.severityConversions)
        counts = (s[2] for s in self._object.getEventSummary())
        return dict(zip(sevs, counts))


def _removeZportDmd(path):
    if path.startswith('/zport/dmd'):
        path = path[10:]
    return path


class DeviceFacade(TreeFacade):
    """
    Facade for device stuff.
    """
    implements(IDeviceFacade)

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

