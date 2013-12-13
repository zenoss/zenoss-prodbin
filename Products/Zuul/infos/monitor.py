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

from Products.ZenModel.interfaces import IMonitor
from Products.Zuul.interfaces import IMonitorInfo, IMonitorTreeNode
from Products.Zuul.infos import ProxyProperty, InfoBase


@adapter(IMonitor)
@implementer(IMonitorTreeNode)
class MonitorTreeNode(object):
    """
    """

    def __init__(self, context, root=None, parent=None):
        """
        """
        self._ctx = context
        self._children = []

    @property
    def type(self):
        return "collector"

    @property
    def id(self):
        # get full zodb path
        return '.'.join(self._ctx.getPhysicalPath())

    @property
    def path(self):
        # Return the path relative to the organizer
        return '/'.join(self._ctx.getPhysicalPath())

    uid = path

    @property
    def name(self):
        # get full zodb path
        return self._ctx.id

    @property
    def text(self):
        # Name of the monitor
        return self._ctx.id

    @property
    def leaf(self):
        return False

    @property
    def children(self):
        return self._children
        
@implementer(IMonitorInfo)
class MonitorInfo(InfoBase):
    """
    """
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
    pingCycleInterval = ProxyProperty('pingCycleInterval')
    modelerCycleInterval = ProxyProperty('modelerCycleInterval')

    @property
    def discoveryNetworks(self):
        return ",".join(self._object.discoveryNetworks)

    @discoveryNetworks.setter
    def discoveryNetworks(self, value):
        self._object.discoveryNetworks = value.split(",")
