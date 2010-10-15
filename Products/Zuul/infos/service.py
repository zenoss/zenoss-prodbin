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

from zope.component import adapts
from zope.interface import implements
from Products.Zuul import getFacade
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase
from Products.Zuul.interfaces import IServiceInfo, IIpServiceClassInfo
from Products.Zuul.interfaces import IServiceOrganizerNode, IWinServiceClassInfo
from Products.Zuul.interfaces import ICatalogTool, IServiceOrganizerInfo
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.IpServiceClass import IpServiceClass
from Products.ZenModel.WinServiceClass import WinServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.Service import Service
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo
from Products.Zuul.utils import catalogAwareImap

class ServiceOrganizerNode(TreeNode):
    implements(IServiceOrganizerNode)
    adapts(ServiceOrganizer)

    @property
    def iconCls(self):
        return ''

    @property
    def _get_cache(self):
        cache = getattr(self._root, '_cache', None)
        if cache is None:
            cache = TreeNode._buildCache(self, ServiceOrganizer, ServiceClass,
                                         'serviceclasses')
        return cache

    @property
    def text(self):
        text = super(ServiceOrganizerNode, self).text
        count = self._get_cache.count(self.uid)
        return {'text': text, 'count': count}

    @property
    def children(self):
        orgs = self._get_cache.search(self.uid)
        return catalogAwareImap(lambda x:ServiceOrganizerNode(x, self._root,
                                                              self), orgs)

    @property
    def leaf(self):
        return False


class ServiceInfoBase(InfoBase):

    def getZMonitor(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zMonitor', True, translate)

    def getZFailSeverity(self):
        def translate(rawValue):
            return {5: 'Critical',
                    4: 'Error',
                    3: 'Warning',
                    2: 'Info',
                    1: 'Debug'}[rawValue]
        return getZPropertyInfo(self._object, 'zFailSeverity', 4, translate)

    def setZFailSeverity(self, data):
        setZPropertyInfo(self._object, 'zFailSeverity', **data)

    zFailSeverity = property(getZFailSeverity, setZFailSeverity)


class ServiceInfo(ServiceInfoBase):
    implements(IServiceInfo)

    def setZMonitor(self, data):
        oldZMonitor = self._object.zMonitor
        setZPropertyInfo(self._object, 'zMonitor', **data)
        if self._object.zMonitor != oldZMonitor:
            self._object._indexInstances()

    zMonitor = property(ServiceInfoBase.getZMonitor, setZMonitor)

    def getServiceKeys(self):
        return self._object.serviceKeys

    def setServiceKeys(self, value):
        self._object.serviceKeys = value

    serviceKeys = property(getServiceKeys, setServiceKeys)

    @property
    def count(self):
        numInstances = ICatalogTool(self._object).count(
            (Service,), self.uid)
        return numInstances

class IpServiceClassInfo(ServiceInfo):
    adapts(IpServiceClass)
    implements(IIpServiceClassInfo)

    def getPort(self):
        return self._object.port

    def setPort(self, value):
        self._object.port = value

    port = property(getPort, setPort)

    def getSendString(self):
        return self._object.sendString

    def setSendString(self, value):
        self._object.sendString = value

    sendString = property(getSendString, setSendString)

    def getExpectRegex(self):
        return self._object.expectRegex

    def setExpectRegex(self, value):
        self._object.expectRegex = value

    expectRegex = property(getExpectRegex, setExpectRegex)


class WinServiceClassInfo(ServiceInfo):
    adapts(WinServiceClass)
    implements(IWinServiceClassInfo)

    def getMonitoredStartModes(self):
        return self._object.monitoredStartModes

    def setMonitoredStartModes(self, value):
        self._object.monitoredStartModes = value.split(',')

    monitoredStartModes = property(getMonitoredStartModes, setMonitoredStartModes)

class ServiceOrganizerInfo(ServiceInfoBase):
    implements(IServiceOrganizerInfo)
    adapts(ServiceOrganizer)

    def setZMonitor(self, data):
        oldZMonitor = self._object.zMonitor
        setZPropertyInfo(self._object, 'zMonitor', **data)
        if self._object.zMonitor != oldZMonitor:
            self._object._indexServiceClassInstances()

    zMonitor = property(ServiceInfoBase.getZMonitor, setZMonitor)
