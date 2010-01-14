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

class DeviceOrganizerNode(TreeNode):
    implements(IDeviceOrganizerNode)
    adapts(DeviceOrganizer)

    uiProvider = 'hierarchy'

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
        severities = [c[0].lower() for c in manager.severityConversions]
        counts = [s[2] for s in self._object.getEventSummary()]
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

    def moveDevices(self, uids, target):
        # Resolve target if a path
        if isinstance(target, basestring):
            target = self._findObject(target)
        assert isinstance(target, DeviceOrganizer)
        devs = (self._findObject(uid) for uid in uids)
        if isinstance(target, DeviceGroup):
            for dev in devs:
                paths = set(g.getPrimaryId() for g in dev.groups())
                paths.add(target.getPrimaryId())
                dev.setGroups(map(_removeZportDmd, paths))
        elif isinstance(target, System):
            for dev in devs:
                paths = set(g.getPrimaryId() for g in dev.systems())
                paths.add(target.getPrimaryId())
                dev.setSystems(map(_removeZportDmd, paths))
        elif isinstance(target, Location):
            for dev in devs:
                dev.setLocation(_removeZportDmd(target.getPrimaryId()))
        elif isinstance(target, DeviceClass):
            self._dmd.Devices.moveDevices(_removeZportDmd(target.getPrimaryId()),
                                          [dev.id for dev in devs])

