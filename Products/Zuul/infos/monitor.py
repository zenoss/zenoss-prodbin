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
from Products.Zuul.infos import ProxyProperty

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

    uid=path
    
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

    eventlogCycleInterval = ProxyProperty('eventlogCycleInterval')
    processCycleInterval = ProxyProperty('processCycleInterval')
    statusCycleInterval = ProxyProperty('statusCycleInterval')
    winCycleInterval = ProxyProperty('winCycleInterval')
    wmibatchSize = ProxyProperty('wmibatchSize')
    wmiqueryTimeout = ProxyProperty('wmiqueryTimeout')
    configCycleInterval = ProxyProperty('configCycleInterval')
    zenProcessParallelJobs = ProxyProperty('zenProcessParallelJobs')
    pingTimeOut = ProxyProperty('pingTimeOut')
    pingTries = ProxyProperty('pingTries')
    pingChunk = ProxyProperty('pingChunk')
    pingCycleInterval = ProxyProperty('pingCycleInterval')
    maxPingFailures = ProxyProperty('maxPingFailures')
    modelerCycleInterval = ProxyProperty('modelerCycleInterval')
    
    @property
    def discoveryNetworks(self):
        return ",".join(self._object.discoveryNetworks)
 
    @discoveryNetworks.setter
    def discoveryNetworks(self, value):
        self._object.discoveryNetworks = value.split(",")
