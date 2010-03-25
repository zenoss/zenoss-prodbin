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

from itertools import imap, chain
from zope.component import adapts
from zope.interface import implements
from Products.Zuul import getFacade
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase
from Products.Zuul.interfaces import IServiceEntity, IServiceInfo
from Products.Zuul.interfaces import IServiceNode, IServiceOrganizerNode
from Products.Zuul.interfaces import ICatalogTool
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.Service import Service

class ServiceNode(TreeNode):
    implements(IServiceNode)
    adapts(IServiceEntity)

    uiProvider = 'hierarchy'

    @property
    def _evsummary(self):
        return getFacade('service').getEventSummary(self.uid)

    @property
    def text(self):
        text = super(ServiceNode, self).text
        numInstances = ICatalogTool(self._object).count(
            (Service,), self.uid)
        return {
            'text': text,
            'count': numInstances,
            'description': 'instances'
        }

    @property
    def children(self):
        cat = ICatalogTool(self._object)
        orgs = cat.search(ServiceOrganizer, paths=(self.uid,), depth=1)
        # Must search at depth+1 to account for relationship
        cls = cat.search(ServiceClass, paths=(self.uid,), depth=2)
        return imap(ServiceNode, chain(orgs, cls))

    @property
    def leaf(self):
        return 'serviceclasses' in self.uid

class ServiceOrganizerNode(ServiceNode):
    implements(IServiceOrganizerNode)
    adapts(ServiceOrganizer)

    def __init__(self, brain):
        super(ServiceOrganizerNode, self).__init__(brain)

    @property
    def children(self):
        cat = ICatalogTool(self._object)
        orgs = cat.search(ServiceOrganizer, paths=(self.uid,), depth=1)
        return imap(ServiceOrganizerNode, orgs)

    @property
    def leaf(self):
        return False

class ServiceInfo(InfoBase):
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


