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

import logging
from itertools import imap, chain
from zope.component import adapts
from zope.interface import implements
from Products.Zuul.tree import TreeNode
from Products.Zuul.facades import TreeFacade, InfoBase
from Products.Zuul.interfaces import ITreeFacade
from Products.Zuul.interfaces import IServiceFacade
from Products.Zuul.interfaces import IServiceEntity
from Products.Zuul.interfaces import IServiceInfo, IServiceOrganizerInfo
from Products.Zuul.interfaces import IServiceNode,ICatalogTool
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer
from Products.ZenModel.IpService import IpService
from Products.ZenModel.WinService import WinService

log = logging.getLogger('zen.ServiceFacade')

class ServiceNode(TreeNode):
    implements(IServiceNode)
    adapts(IServiceEntity)

    uiProvider = 'hierarchy'

    @property
    def iconCls(self):
        sev = 'clear' # FIXME: Get this somehow
        return 'severity-icon-small %s' % sev

    @property
    def text(self):
        text = super(ServiceNode, self).text
        numInstances = ICatalogTool(self._object).count(
            (IpService, WinService), self.uid)
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



class ServiceFacade(TreeFacade):
    implements(IServiceFacade, ITreeFacade)

    def _root(self):
        return self._dmd.Services

    @property
    def _instanceClass(self):
        return "Products.ZenModel.Service.Service"
