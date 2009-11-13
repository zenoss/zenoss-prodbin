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
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IProcessFacade
from Products.Zuul.interfaces import IProcessTree
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.interfaces import ISerializableFactory
from Products.ZenModel.OSProcessClass import OSProcessClass


class ProcessTree(object):
    implements(IProcessTree)
    
    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either an 
        OSProcessOrganizer or an OSProcessClass.
        """
        self._object = object
    
    @property
    def id(self):
        path = list(self._object.getPrimaryPath()[3:])
        if 'osProcessClasses' in path:
            path.remove('osProcessClasses')
        return '/'.join(path)
        
    @property
    def text(self):
        return self._object.titleOrId()
        
    @property
    def children(self):
        managers = []
        if not self.leaf:
            obj = self._object
            managers.extend(obj.objectValues(spec='OSProcessOrganizer'))
            rel = obj._getOb('osProcessClasses')
            managers.extend(rel.objectValues(spec='OSProcessClass'))
        return [ProcessTree(manager) for manager in managers]
        
    @property
    def leaf(self):
        return isinstance(self._object, OSProcessClass)
        
    def __repr__(self):
        return "<ProcessTree(id=%s)>" % (self.id)
        
        
class SerializableProcessTreeFactory(object):
    implements(ISerializableFactory)
    adapts(ProcessTree)
    
    def __init__(self, processTree):
        self._processTree = processTree
    
    def __call__(self):
        obj = {'id': self._processTree.id, 'text': self._processTree.text}
        if self._processTree.leaf:
            obj['leaf'] = True
        else:
            obj['children'] = []
            for childProcessTree in self._processTree.children:
                serializableFactory = ISerializableFactory(childProcessTree)
                obj['children'].append(serializableFactory())
        return obj


class ProcessInfo(object):
    implements(IProcessInfo)
    
    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either an 
        OSProcessOrganizer or an OSProcessClass.
        """
        self._object = object
        
    @property
    def name(self):
        return self._object.titleOrId()
        
    @property
    def description(self):
        return self._object.description
        
    @property
    def monitor(self):
        return self._object.zMonitor
        
    @property
    def failSeverity(self):
        return self._object.zFailSeverity
        
    @property
    def regex(self):
        return getattr(self._object, 'regex', None)
        
    @property
    def ignoreParameters(self):
        return getattr(self._object, 'ignoreParameters', None)
        
    def __repr__(self):
        return "<ProcessInfo(name=%s)>" % (self.name)
        
        
class SerializableProcessInfoFactory(object):
    implements(ISerializableFactory)
    adapts(ProcessInfo)
    
    def __init__(self, processInfo):
        self._processInfo = processInfo
    
    def __call__(self):
        return {'name': self._processInfo.name,
                'description': self._processInfo.description,
                'monitor': self._processInfo.monitor,
                'failSeverity': self._processInfo.failSeverity,
                'regex': self._processInfo.regex,
                'ignoreParameters': self._processInfo.ignoreParameters
                }
                
                
class ProcessFacade(ZuulFacade):
    implements(IProcessFacade)
    
    def getProcessTree(self, processTreeId):
        obj = self._findObject(processTreeId)
        return ProcessTree(obj)
        
    def getProcessInfo(self, processTreeId):
        obj = self._findObject(processTreeId)
        return ProcessInfo(obj)
        
    def _findObject(self, processTreeId):
        parts = processTreeId.split('/')
        objectId = parts[-1]
        if len(parts) == 1:
            manager = self._dmd
        else:
            parentPath = '/'.join(parts[:-1])
            parent = self._dmd.findChild(parentPath)
            if objectId in parent.objectIds():
                manager = parent
            else:
                manager = parent._getOb('osProcessClasses')
        return manager._getOb(objectId)
        
