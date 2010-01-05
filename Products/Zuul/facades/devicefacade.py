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
from Products.Zuul.interfaces import IDeviceFacade, IDeviceClassNode
from Products.Zuul.interfaces import IDeviceClass, IDeviceInfo, IDevice
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.facades import InfoBase
from Products.ZenUtils import IpUtil

class DeviceClassNode(TreeNode):
    implements(IDeviceClassNode)
    adapts(IDeviceClass)

    @property
    def children(self):
        cat = ICatalogTool(self._object)
        orgs = cat.search(IDeviceClass, paths=(self.uid,), depth=1)
        return imap(DeviceClassNode, orgs)

    @property
    def text(self):
        text = super(DeviceClassNode, self).text
        cat = ICatalogTool(self._object)
        numInstances = cat.count('Products.ZenModel.Device.Device', self.uid)
        return {
            'text': text,
            'count': numInstances,
            'description': 'devices'
        }

    # Everything is potentially a branch, just some have no children.
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

