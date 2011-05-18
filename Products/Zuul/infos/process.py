###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from itertools import chain
from zope.component import adapts
from zope.interface import implements
from Products.ZenModel.OSProcess import OSProcess
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer
from Products.Zuul import getFacade
from Products.Zuul.interfaces import IProcessNode
from Products.Zuul.interfaces import IProcessEntity
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.interfaces import IProcessInfo
from Products.Zuul.tree import TreeNode
from Products.Zuul.infos import InfoBase
from Products.Zuul.utils import getZPropertyInfo, setZPropertyInfo
from Products.Zuul.utils import catalogAwareImap

class ProcessNode(TreeNode):
    implements(IProcessNode)
    adapts(IProcessEntity)

    @property
    def iconCls(self):
        return ''

    @property
    def text(self):
        text = super(ProcessNode, self).text
        obj = self._object.getObject()
        count = obj.countClasses()
        return {
            'text': text,
            'count': count,
            'description': 'instances'
        }

    @property
    def _get_cache(self):
        cache = getattr(self._root, '_cache', None)
        if cache is None:
            cache = TreeNode._buildCache(self, OSProcessOrganizer)
            cat = ICatalogTool(self._object.unrestrictedTraverse(self.uid))
            cache.insert(cache._instanceidx, cat.search(OSProcess),
                         ('osProcessClasses', 'instances'),
                         '/zport/dmd/Processes')
        return cache

    @property
    def children(self):
        orgs = self._object.getObject().children()
        orgs.sort(key=lambda x: x.titleOrId())
        return catalogAwareImap(lambda x:ProcessNode(x, self._root, self), orgs)

    @property
    def leaf(self):
        return 'osProcessClasses' in self.uid

class ProcessInfo(InfoBase):
    implements(IProcessInfo)
    adapts(IProcessEntity)

    def getDescription(self):
        return self._object.description
    def setDescription(self, description):
        self._object.description = description
    description = property(getDescription, setDescription)

    def getZMonitor(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zMonitor', True, translate)

    def setZMonitor(self, data):
        setZPropertyInfo(self._object, 'zMonitor', **data)

    zMonitor = property(getZMonitor, setZMonitor)

    def getZAlertOnRestart(self):
        def translate(rawValue):
            return {False: 'No', True: 'Yes'}[rawValue]
        return getZPropertyInfo(self._object, 'zAlertOnRestart', True, translate)

    def setZAlertOnRestart(self, data):
        setZPropertyInfo(self._object, 'zAlertOnRestart', **data)

    zAlertOnRestart = property(getZAlertOnRestart, setZAlertOnRestart)

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

    def getHasRegex(self):
        return isinstance(self._object, OSProcessClass)

    def setHasRegex(self, hasRegex):
        pass

    hasRegex = property(getHasRegex, setHasRegex)

    def getRegex(self):
        return getattr(self._object, 'regex', None)

    def setRegex(self, regex):
        if self.hasRegex:
            self._object.regex = regex

    regex = property(getRegex, setRegex)

    def getIgnoreParameters(self):
        return getattr(self._object, 'ignoreParameters', None)

    def setIgnoreParameters(self, ignoreParameters):
        if self.hasRegex:
            self._object.ignoreParameters = ignoreParameters

    ignoreParameters = property(getIgnoreParameters, setIgnoreParameters)

    def getExample(self):
        return getattr(self._object, 'example', '')

    def setExample(self, example):
        if self.hasRegex:
            self._object.example = example

    example = property(getExample, setExample)

    @property
    def count(self):
        if isinstance(self._object, OSProcessOrganizer):
            return self._object.countClasses()
        # it is an instance
        return self._object.count()
