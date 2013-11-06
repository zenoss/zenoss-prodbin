##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from zope.component import adapter
from zope.interface import implementer

from Products.Zuul.interfaces import (
    IMonitorInfo, IMonitorFacade, IMonitorTreeNode
)
from Products.Zuul.decorators import memoize
from Products.Zuul.tree import TreeNode


@adapter(IMonitorFacade)
@implementer(IMonitorTreeNode)
class MonitorTreeNode(object):
    """
    """

    def __init__(self, context, root=None, parent=None):
        """
        """
        self._ctx = context

    @property
    def id(self):
        # get full zodb path
        return self._ctx.uid

    @property
    def path(self):
        # Return the path relative to the organizer
        return self._ctx.uid

    @property
    def name(self):
        # get full zodb path
        return self._ctx.name

    @property
    def text(self):
        # Name of the monitor
        return self._ctx.name

    @property
    def children(self):
        return []

    # Monitor's don't have children, so they are leaf nodes.
    leaf = True


@implementer(IMonitorInfo)
class MonitorInfo(object):
    """
    """

    def __init__(self, monitor):
        """
        Initialize an instance of MonitorInfo.

        :param IMonitor monitor: The IMonitor object.
        """
        self._object = monitor

    @property
    def eventlogCycleInterval(self):  # = Int()
        return self._object.getProperty("eventlogCycleInterval")

    @eventlogCycleInterval.setter
    def eventlogCycleInterval(self, value):
        pass

    @property
    def processCycleInterval(self):  # = Int()
        return self._object.getProperty("processCycleInterval")

    @property
    def statusCycleInterval(self):  # = Int()
        return self._object.getProperty("statusCycleInterval")

    @property
    def winCycleInterval(self):  # = Int()
        return self._object.getProperty("winCycleInterval")

    @property
    def wmibatchSize(self):  # = Int()
        return self._object.getProperty("wmibatchSize")

    @property
    def wmiqueryTimeout(self):  # = Int()
        return self._object.getProperty("wmiqueryTimeout")

    @property
    def configCycleInterval(self):  # = Int()
        return self._object.getProperty("configCycleInterval")

    @property
    def zenProcessParallelJobs(self):  # = Int()
        return self._object.getProperty("zenProcessParallelJobs")

    @property
    def pingTimeOut(self):  # = Float()
        return self._object.getProperty("pingTimeOut")

    @property
    def pingTries(self):  # = Int()
        return self._object.getProperty("pingTries")

    @property
    def pingChunk(self):  # = Int()
        return self._object.getProperty("pingChunk")

    @property
    def pingCycleInterval(self):  # = Int()
        return self._object.getProperty("pingCycleInterval")

    @property
    def maxPingFailures(self):  # = Int()
        return self._object.getProperty("maxPingFailures")

    @property
    def modelerCycleInterval(self):  # = Int()
        return self._object.getProperty("modelerCycleInterval")

    @property
    def discoveryNetworks(self):  # = List()
        return self._object.getProperty("discoveryNetworks")
