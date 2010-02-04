###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
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
from Products.Zuul.interfaces import IDeviceOrganizerNode
from Products.Zuul.interfaces import IDeviceOrganizerInfo
from Products.Zuul.interfaces import IDeviceInfo, IDevice, ICatalogTool
from Products.Zuul.infos import InfoBase
from Products.ZenModel.DeviceOrganizer import DeviceOrganizer
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

    def getIpAddress(self):
        if self._object.manageIp:
            return IpUtil.ipToDecimal(self._object.manageIp)

    def setIpAddress(self, ip=None):
        self._object.setManageIp(ip)

    ipAddress = property(getIpAddress, setIpAddress)

    def getProductionState(self):
        return self._object.convertProdState(self._object.productionState)

    def setProductionState(self, prodState):
        self._object.setProdState(int(prodState))

    productionState = property(getProductionState, setProductionState)

    def getPriority(self):
        return self._object.convertPriority(self._object.priority)

    def setPriority(self, priority):
        self._object.setPriority(priority)

    priority = property(getPriority, setPriority)

    def getCollectorName(self):
        return self.object.getPerformanceServerName()

    def setCollector(self, collector):
        self._object.setPerformanceMonitor(collector)

    collector = property(getCollectorName, setCollector)

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

