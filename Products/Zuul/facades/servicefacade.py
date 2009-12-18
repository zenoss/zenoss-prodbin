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
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import ITreeFacade
from Products.Zuul.interfaces import IServiceFacade
from Products.Zuul.interfaces import IServiceEntity
from Products.Zuul.interfaces import IServiceInfo, IServiceOrganizerInfo, IInfo
from Products.Zuul.interfaces import IServiceNode, ITreeNode
from Products.Zuul.interfaces import IDeviceInfo, IEventInfo
from Products.ZenModel.ServiceClass import ServiceClass
from Products.ZenModel.ServiceOrganizer import ServiceOrganizer

class ServiceNode(TreeNode):
    implements(IServiceNode)
    adapts(IServiceEntity)

    uiProvider = 'hierarchy'
        
    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either a 
        ServiceOrganizer or a ServiceClass.
        """
        self._object = object

    @property
    def iconCls(self):
        sev = 'clear' # FIXME: Get this somehow
        return 'severity-icon-small %s' % sev
    
    @property
    def id(self):
        path = list(self._object.getPrimaryPath()[3:])
        if 'ServiceClasses' in path:
            path.remove('ServiceClasses')
        return '/'.join(path)
        
    @property
    def text(self):
        text = super(ServiceNode, self).text
        numInstances = 3 # FIXME: Get this somehow
        return {
            'text': text,
            'count': numInstances,
            'description': 'instances'
        }
        
    @property
    def children(self):
        managers = []
        if not self.leaf:
            managers.extend(self._object.objectValues(spec='ServiceOrganizer'))
            rel = self._object._getOb('serviceclasses')
            managers.extend(rel.objectValues(spec='ServiceClass'))
        return imap(ITreeNode, managers)

    @property
    def leaf(self):
        return isinstance(self._object, ServiceClass)

    def __repr__(self):
        return "<ServiceNode(id=%s)>" % (self.id)  

# TODO: Abstract ServiceOrganizerInfo into a generic OrganizerInfo
class ServiceOrganizerInfo(object):
    implements(IServiceOrganizerInfo)
    adapts(ServiceOrganizer)

    def __init__(self, service):
        """
        The object parameter is the wrapped persistent object. 
        """
        self._object = service

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
    
    def __repr__(self):
        return "<ServiceOrganizerInfo(name=%s)>" % (self.name)  

class ServiceInfo(object):
    implements(IServiceInfo)
    adapts(ServiceClass)

    def __init__(self, service):
        """
        The object parameter is the wrapped persistent object.
        """
        self._object = service

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


              
class ServiceFacade(ZuulFacade):
    implements(IServiceFacade, ITreeFacade)
    
    def getTree(self, id):
        obj = self._findObject(id)
        return ITreeNode(obj)

    def getInfo(self, id):
        obj = self._findObject(id)
        return IInfo(obj)

    def getDevices(self, id):
        serviceClasses = self._getClasses(id)
        deviceInfos = []
        infoClass = None
        for serviceClass in serviceClasses:
            for instance in serviceClass.instances():
                newDeviceInfo = IDeviceInfo(instance.device())
                if infoClass is None:
                    infoClass = newDeviceInfo.__class__
                for existingDeviceInfo in deviceInfos:
                    if existingDeviceInfo.device == newDeviceInfo.device:
                        break
                else:
                    deviceInfos.append(newDeviceInfo)
        if infoClass is not None:
            deviceInfos.sort(key=infoClass.getDevice)
        return deviceInfos

    def getEvents(self, id):
        serviceClasses = self._getClasses(id)
        zem = self._dmd.ZenEventManager
        eventInfos = []
        for serviceClass in serviceClasses:
            for instance in serviceClass.instances():
                for event in zem.getEventListME(instance):
                    if not getattr(event, 'device', None):
                        event.device = instance.device().id
                    if not getattr(event, 'component', None):
                        event.component = instance.name()
                    eventInfos.append(IEventInfo(event))
        return eventInfos

    def _findObject(self, treeId):
        parts = treeId.split('/')
        objectId = parts[-1]
        if len(parts) == 1:
            manager = self._dmd
        else:
            parentPath = '/'.join(parts[:-1])
            parent = self._dmd.findChild(parentPath)
            if objectId in parent.objectIds():
                manager = parent
            else:
                manager = parent._getOb('ServiceClasses')
        return manager._getOb(objectId)

    def _getClasses(self, id):
        obj = self._findObject(id)
        if isinstance(obj, ServiceOrganizer):
            classes = obj.getSubClassesSorted()
        else:
            classes = [obj]
        return classes
    