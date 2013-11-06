##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import Attribute

from ..form.schema import Int, Float, List
from . import IInfo, ITreeNode, IFacade


class IMonitorTreeNode(ITreeNode):
    """
    """


class IMonitorInfo(ITreeNode):
    """
    Set of attributes describing a performance monitor.
    """

    eventlogCycleInterval = Int()
    processCycleInterval = Int()
    statusCycleInterval = Int()
    winCycleInterval = Int()
    wmibatchSize = Int()
    wmiqueryTimeout = Int()
    configCycleInterval = Int()
    zenProcessParallelJobs = Int()
    pingTimeOut = Float()
    pingTries = Int()
    pingChunk = Int()
    pingCycleInterval = Int()
    maxPingFailures = Int()
    modelerCycleInterval = Int()
    discoveryNetworks = List()


class IMonitorFacade(IFacade):
    """
    An interface describing a means for interacting with a monitor.
    """

    name = Attribute("The name of the monitor")
    uid = Attribute("The monitor's unique identifier")

    def queryDevices(name=None, cls=None):
        """
        Returns an iterable that produces IDevice objects associated with
        this monitor.
        """

    def getProperties():
        """
        Returns a dict containing the Monitor's properties.
        """

    def updateProperties(**properties):
        """
        Update the Monitor's properties from the given keyword arguments.
        Unknown properties are ignored.  A BadRequest exception is raised
        if a given property is not writable.
        """

    def getProperty(self, name):
        """
        Returns the value of the named property.
        """

    def setProperty(self, name, value):
        """
        Sets the value of the named property.
        """


class IMonitorManagerFacade(IFacade):
    """
    An interface describing how to lookup, create, edit, and delete
    IMonitor objects.
    """

    def queryPerformanceMonitors(name="*"):
        """
        Return a sequence of IMonitor objects.
        """

    def getPerformanceMonitor(id):
        """
        Return the IMonitor object having the specified ID.
        """

    def createPerformanceMonitor(id, sourceId=None):
        """
        Creates a new performance monitor.  The new monitor is created as
        a copy of the monitor given by sourceId.  If sourceId is not
        specified, then the default monitor is the source.

        The IMonitorInfo object of the new monitor is returned.
        """

    def deletePerformanceMonitor(id):
        """
        Deletes the identified performance monitor.
        """
