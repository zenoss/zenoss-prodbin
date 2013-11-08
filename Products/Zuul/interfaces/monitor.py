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
from Products.Zuul.utils import ZuulMessageFactory as _t

class IMonitorTreeNode(ITreeNode):
    """
    """


class IMonitorInfo(IInfo):
    """
    Set of attributes describing a performance monitor.
    """
    eventlogCycleInterval = Int(title=_t("Event Log Cycle Interval (seconds)"),
    description=_t("How often zeneventlog collects events"))
    
    processCycleInterval = Int(title=_t("Process Cycle Interval (seconds)"),
    description=_t("How often zenprocess collects performance metrics about running processes"))
    
    statusCycleInterval = Int(title=_t("Status Cycle Interval (seconds)"),
    description=_t("How often zenstatus polls tests configured ports"))
    
    winCycleInterval = Int(title=_t("Windows Cycle Interval (seconds)"),
    description=_t("How often zenwinperf collects performance metrics")
    )
    wmibatchSize = Int(title=_t("WMI Batch Size"),
    description=_t("Size of the number of WMI queries we issue at a time"))
    
    wmiqueryTimeout = Int(title=_t("WMI Query Timeout (seconds)"),
    description=_t("How long zeneventlog and zenwin will wait on a WMI response when collecting"))
    
    configCycleInterval = Int(title=_t("Config Cycle Interval (minutes)"),
    description=_t("The interval, specified in minutes, that the collector&apos;s configuration will be updated from the ZenHub service"))
    
    pingTimeOut = Float(title=_t("Ping Timeout (milliseconds)"),
    description=_t("How long zenping will wait before timing out a ping request"))
    
    pingTries = Int(title=_t("Ping Tries"),
    description=_t("Number of times zenping will attempt to ping a device"))
    
    pingCycleInterval = Int(title=_t("Ping Cycle Interval (seconds)"),
    description=_t("How often zenping will attempt to ping devices"))
        
    modelerCycleInterval = Int(title=_t("Modeler Cycle Interval (minutes)"),
    description=_t("How often zenmodeler will remodel devices"))
    
    discoveryNetworks = List(title=_t("Discovery Networks"),
    description=_t("Comma separated list of subnets that zendisc will run discovery on"))


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
