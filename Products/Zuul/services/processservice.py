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

from zope.interface import implements
from Products.Zuul.services import ZuulService
from Products.Zuul.interfaces import *
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
        children = []
        if not self.leaf:
            for osProcessOrganizer in self._object.children():
                children.append(osProcessOrganizer)
            for osProcessClass in self._object.osProcessClasses():
                children.append(osProcessClass)
        return [ProcessTree(child) for child in children]
        
    @property
    def leaf(self):
        return isinstance(self._object, OSProcessClass)
        
    @property
    def serializableObject(self):
        obj = {'id': self.id, 'text': self.text}
        if self.leaf:
            obj['leaf'] = True
        else:
            obj['children'] = [c.serializableObject for c in self.children]
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
        
    @property
    def serializableObject(self):
        return {'name': self.name,
                'description': self.description,
                'monitor': self.monitor,
                'failSeverity': self.failSeverity,
                'regex': self.regex,
                'ignoreParameters': self.ignoreParameters
                }
        
        
class ProcessService(ZuulService):
    implements(IProcessService)
    
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
        
