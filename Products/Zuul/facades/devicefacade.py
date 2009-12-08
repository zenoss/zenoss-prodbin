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
from Products.Zuul.interfaces import IDeviceClassFacade, IDeviceClassNode
from Products.Zuul.interfaces import IDeviceClassInfo, IDeviceClass, ITreeFacade
from Products.Zuul.interfaces import IDeviceClass
from Products.Zuul.interfaces import IDeviceInfo, IDevice
from Products.ZenUtils import IpUtil

class DeviceClassNode(TreeNode):
    implements(IDeviceClassNode)
    adapts(IDeviceClass)

    @property
    def id(self):
        path = self._object.getPrimaryUrlPath()[:3]
        return '/'.join(path)

    @property
    def children(self):
        return imap(ITreeNode, self._object.objectValues(spec='DeviceClass'))

    # Everything is potentially a branch, just some have no children.
    leaf = False


class DeviceClassInfo(object):
    implements(IDeviceClassInfo)
    adapts(IDeviceClass)

    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either an
        OSProcessOrganizer or an OSProcessClass.
        """
        self._object = object

    @property
    def name(self):
        return self._object.titleOrId()

class DeviceInfo(object):
    implements(IDeviceInfo)
    adapts(IDevice)

    def __init__(self, object):
        self._object = object

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

    def __repr__(self):
        return "<DeviceInfo(device=%s)>" % (self.device)

class DeviceFacade(TreeFacade):
    """
    Facade for device stuff.
    """
    implements(IDeviceClassFacade)


