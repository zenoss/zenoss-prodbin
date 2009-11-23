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
from Products.Zuul.interfaces import IProcessFacade, IProcessEntity
from Products.Zuul.interfaces import ITreeFacade
from Products.Zuul.interfaces import IProcessInfo, IInfo
from Products.Zuul.interfaces import ISerializableFactory
from Products.Zuul.interfaces import IProcessNode, ITreeNode
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer


class ProcessNode(TreeNode):
    implements(IProcessNode)
    adapts(IProcessEntity)

    uiProvider = 'hierarchy'

    def __init__(self, object):
        """
        The object parameter is the wrapped persistent object. It is either an
        OSProcessOrganizer or an OSProcessClass.
        """
        self._object = object

    @property
    def iconCls(self):
        sev = 'clear' # FIXME: Get this somehow
        return 'severity-icon-small %s' % sev

    @property
    def text(self):
        text = super(ProcessNode, self).text
        numInstances = 3 # FIXME: Get this somehow
        return {
            'text': text,
            'count': numInstances,
            'description': 'instances'
        }

    @property
    def id(self):
        path = list(self._object.getPrimaryPath()[3:])
        if 'osProcessClasses' in path:
            path.remove('osProcessClasses')
        return '/'.join(path)

    @property
    def children(self):
        managers = []
        if not self.leaf:
            obj = self._object
            managers.extend(obj.objectValues(spec='OSProcessOrganizer'))
            rel = obj._getOb('osProcessClasses')
            managers.extend(rel.objectValues(spec='OSProcessClass'))
        return imap(ITreeNode, managers)

    @property
    def leaf(self):
        return isinstance(self._object, OSProcessClass)

    def __repr__(self):
        return "<ProcessTree(id=%s)>" % (self.id)


class ProcessInfo(object):
    implements(IProcessInfo)
    adapts(OSProcessClass)

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
    implements(IProcessFacade, ITreeFacade)

    def getTree(self, root):
        obj = self._findObject(root)
        return ITreeNode(obj)

    def getInfo(self, nodeid):
        obj = self._findObject(nodeid)
        return IInfo(obj)

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

