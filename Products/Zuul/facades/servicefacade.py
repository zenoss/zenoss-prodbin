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
from Products.Zuul.facades import TreeFacade
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


# TODO: Abstract ServiceOrganizerInfo into a generic OrganizerInfo
class ServiceOrganizerInfo(object):
    implements(IServiceOrganizerInfo)
    adapts(ServiceOrganizer)

    def __init__(self, service):
        """
        The object parameter is the wrapped persistent object. 
        """
        self._object = service

    @property
    def uid(self):
        return '/'.join(self._object.getPrimaryPath())

    def getName(self):
        return self._object.titleOrId()

    def setName(self, name):
        self._object.setTitle(name)

    name = property(getName, setName)

    def getDescription(self):
        return self._object.description

    def setDescription(self, value):
        self._object.description = value

    description = property(getDescription, setDescription) 


class ServiceInfo(object):
    implements(IServiceInfo)
    adapts(ServiceClass)

    def __init__(self, service):
        """
        The object parameter is the wrapped persistent object.
        """
        self._object = service

    @property
    def uid(self):
        return '/'.join(self._object.getPrimaryPath())

    def getName(self):
        return self._object.titleOrId()

    def setName(self, value):
        self._object.name = value

    name = property(getName, setName)

    def getDescription(self):
        return self._object.description

    def setDescription(self, value):
        self._object.description = value

    description = property(getDescription, setDescription) 

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

    def __repr__(self):
        return "<ServiceInfo(name=%s)>" % (self.name)  



class ServiceFacade(TreeFacade):
    implements(IServiceFacade, ITreeFacade)

    def _root(self):
        return self._dmd.Services

    def _instanceClass(self):
        return "Products.ZenModel.Service.Service"
