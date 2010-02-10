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
from Products.Zuul.decorators import info
from Products.Zuul.facades import TreeFacade
from Products.Zuul.interfaces import IDeviceFacade
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

