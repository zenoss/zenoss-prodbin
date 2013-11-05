##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import copy
import logging

from datetime import datetime
from fnmatch import fnmatch

from zope.component import getAdapter, queryAdapter
from zope.interface import implementer

from Products.Zuul.interfaces import (
    IMonitorManagerFacade, IMonitorFacade
)

LOG = logging.getLogger("Zuul.facades")


@implementer(IMonitorManagerFacade)
class MonitorManagerFacade(object):
    """
    """

    def __init__(self, dataroot):
        """
        """
        self._dmd = dataroot
        self._perf = self._dmd.Monitors.Performance

    def queryPerformanceMonitors(self, namePattern=None):
        """
        Returns a sequence of IMonitorInfo objects.
        """
        namePattern = namePattern if (namePattern is not None) else "*"
        monitors = []
        for name in self._perf.getPerformanceMonitorNames():
            if fnmatch(name, namePattern):
                perfmon = self._perf.get(name)
                facade = queryAdapter(perfmon, IMonitorFacade)
                monitors.append(facade)
        return monitors

    def getPerformanceMonitor(self, id, default=None):
        """
        Returns the IApplicationFacade object of the identified application.
        """
        perfmon = self._perf.get(id)
        return queryAdapter(perfmon, IMonitorFacade)


@implementer(IMonitorFacade)
class MonitorFacade(object):
    """
    """

    def __init__(self, monitor):
        self._monitor = monitor

    @property
    def name(self):
        """
        The name of the monitor.
        """
        return self._monitor.id

    @property
    def uuid(self):
        """
        The full ZODB object path of the monitor.
        """
        return '/'.join(self._monitor.getPhysicalPath())

    def getProperties(self):
        """
        """
        return dict(self._monitor.propertyItems())

    def getProperty(self, name):
        """
        Returns the value of the named property.
        """
        return self._monitor.getProperty(name)

    def setProperty(self, name, value):
        """
        Sets the value of the named property.
        """

