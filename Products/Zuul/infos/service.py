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
from Products.Zuul.interfaces import IServiceInfo
from Products.Zuul.interfaces import IServiceOrganizerNode
from Products.Zuul.interfaces import ICatalogTool, IServiceOrganizerInfo
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.Service import Service
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo
from Products.Zuul.utils import catalogAwareImap

class ServiceOrganizerNode(TreeNode):
    implements(IServiceOrganizerNode)
    adapts(ServiceOrganizer)

    @property
    def _evsummary(self):
        return getFacade('service').getEventSummary(self.uid)

    @property
    def text(self):
        text = super(ServiceOrganizerNode, self).text
        count = ICatalogTool(self._object).count((ServiceClass,), self.uid)
        return {'text': text, 'count': count}

    @property
    def children(self):
        cat = ICatalogTool(self._object)
        orgs = cat.search(ServiceOrganizer, paths=(self.uid,), depth=1)
        return catalogAwareImap(ServiceOrganizerNode, orgs)

    @property
    def leaf(self):
        return False


class ServiceInfoBase(InfoBase):

    def getZMonitor(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zMonitor', True, translate)

    def setZMonitor(self, data):
        setZPropertyInfo(self._object, 'zMonitor', **data)

    zMonitor = property(getZMonitor, setZMonitor)

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
    adapts(ServiceClass)

    def getServiceKeys(self):
        return self._object.serviceKeys

    def setServiceKeys(self, value):
        self._object.serviceKeys = value

    serviceKeys = property(getServiceKeys, setServiceKeys)

    def getPort(self):
        return self._object.port

    def setPort(self, value):
        self._object.port = value

    port = property(getPort, setPort)

    @property
    def count(self):
        numInstances = ICatalogTool(self._object).count(
            (Service,), self.uid)

        return numInstances

class ServiceOrganizerInfo(ServiceInfoBase):
    implements(IServiceOrganizerInfo)
    adapts(ServiceOrganizer)
