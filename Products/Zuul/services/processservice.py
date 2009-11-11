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

class ProcessTreeNode(object):
    implements(IProcessTreeNode)
    
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
        return [ProcessTreeNode(child) for child in children]
        
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


class ProcessService(ZuulService):
    implements(IProcessService)
    
    def getProcessTree(self, path='Processes'):
        return ProcessTreeNode(self._dmd.findChild(path))
        
