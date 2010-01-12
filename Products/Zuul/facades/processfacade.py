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
from Products.Zuul.interfaces import IProcessFacade, IProcessEntity
from Products.Zuul.interfaces import ITreeFacade, IProcessInfo
from Products.Zuul.interfaces import IProcessNode, ICatalogTool
from Products.ZenModel.OSProcess import OSProcess
from Products.ZenModel.OSProcessClass import OSProcessClass
from Products.ZenModel.OSProcessOrganizer import OSProcessOrganizer

log = logging.getLogger('zen.ProcessFacade')

class ProcessNode(TreeNode):
    implements(IProcessNode)
    adapts(IProcessEntity)

    uiProvider = 'hierarchy'

    @property
    def iconCls(self):
        sev = 'clear' # FIXME: Get this somehow
        return 'severity-icon-small %s' % sev

    @property
    def text(self):
        text = super(ProcessNode, self).text
        numInstances = ICatalogTool(self._object).count(OSProcess, self.uid)
        return {
            'text': text,
            'count': numInstances,
            'description': 'instances'
        }

    @property
    def children(self):
        cat = ICatalogTool(self._object)
        orgs = cat.search(OSProcessOrganizer, paths=(self.uid,), depth=1)
        # Must search at depth+1 to account for relationship
        cls = cat.search(OSProcessClass, paths=(self.uid,), depth=2)
        return imap(ProcessNode, chain(orgs, cls))

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

    def getIsMonitoringAcquired(self):
        return not self._object.hasProperty('zMonitor') \
                and not self._object.hasProperty('zFailSeverity')

    def setIsMonitoringAcquired(self, isMonitoringAcquired):
        if isMonitoringAcquired:
            for name in 'zMonitor', 'zFailSeverity':
                if self._object.hasProperty(name):
                    self._object.deleteZenProperty(name)

    isMonitoringAcquired = property(getIsMonitoringAcquired,
                                    setIsMonitoringAcquired)

    def getMonitor(self):
        return self._object.zMonitor

    def setMonitor(self, monitor):
        if self._object.hasProperty('zMonitor'):
            self._object._updateProperty('zMonitor', monitor)
        else:
            self._object._setProperty('zMonitor', monitor)

    monitor = property(getMonitor, setMonitor)

    def getEventSeverity(self):
        return self._object.zFailSeverity

    def setEventSeverity(self, eventSeverity):
        if isinstance(eventSeverity, basestring):
            eventSeverity = {'Critical': 5,
                             'Error': 4,
                             'Warning': 3,
                             'Info': 2,
                             'Debug': 1}[eventSeverity]
        if self._object.hasProperty('zFailSeverity'):
            self._object._updateProperty('zFailSeverity', eventSeverity)
        else:
            self._object._setProperty('zFailSeverity', eventSeverity)

    eventSeverity = property(getEventSeverity, setEventSeverity)

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


class ProcessFacade(TreeFacade):
    implements(IProcessFacade, ITreeFacade)

    @property
    def _root(self):
        return self._dmd.Processes

    @property
    def _instanceClass(self):
        return "Products.ZenModel.OSProcess.OSProcess"

