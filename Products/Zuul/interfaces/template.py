###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.Zuul.interfaces import IInfo, IFacade
from Products.Zuul.form import schema

class ITemplateNode(IInfo):
    """
    A template node contains template leaves. It contains all of the templates
    throughout device class hierarchy that share the same id.
    """

class ITemplateLeaf(IInfo):
    """
    A template leaf is a single instance of an RRD template at a specific
    spot in the device class hierarchy.
    """

class IDataSourceInfo(IInfo):
    """
    Adapts RRDDataSource.
    """
    name = schema.Text(title=u"Name",
                       description=u"The name of this datasource",
                       readonly=True)
    type = schema.Text(title=u"Type",
                       readonly=True)
    severity = schema.Text(title=u"Severity",
                           xtype="severity")
    component = schema.Text(title=u"Component")
    oid = schema.Text(title=u"OID")
    eventKey = schema.Text(title=u"Event Key")
    eventClass = schema.Text(title=u"Event Class",
                             xtype="eventclass")
    commandTemplate = schema.TextLine(title=u"Command Template")
    cycleTime = schema.Int(title=u"Cycle Time")
    parser = schema.Text(title=u"Parser",
                         xtype="parser")
    enabled = schema.Bool(title=u"Enabled")
    usessh = schema.Bool(title=u"Use SSH")

    
class IDataPointInfo(IInfo):
    """
    Adapts RRDDataPoint.
    """
    name = schema.Text(title=u"Name",
                       description=u"The name of this data point",
                       readonly=True)
    rrdtype = schema.Text(title=u"Type",
                          description=u"The type of data point we have",
                          xtype="rrdtype")
    createCmd = schema.TextLine(title=u"Create Command")
    rrdmin = schema.Text(title=u"RRD Minimum")
    rrdmax = schema.Text(title=u"RRD Maximum")
    isrow = schema.Bool(title=u"Read Only")
    alias = schema.Text(title=u"Alias",
                        readonly=True)
    
    
class IThresholdInfo(IInfo):
    """
    Adapts ThresholdClass.
    """
    name = schema.Text(title=u"Name",
                       readonly=True, order=1)
    type = schema.Text(title=u"Type",
                       readonly=True, order=2)
    dsnames = schema.List(title=u"DataPoints",
                          xtype="datapointitemselector", order=3)
    severity = schema.Text(title=u"Severity",
                           xtype="severity", order=4)
    enabled = schema.Bool(title=u"Enabled", order=5)
    
class IMinMaxThresholdInfo(IThresholdInfo):
    """
    Adapts the MinMaxThresholdClass
    """
    minval = schema.Int(title=u"Minimum Value", order=6)
    maxval = schema.Int(title=u"Maximum Value", order=7)
    eventClass = schema.Text(title=u"Event Class",
                             xtype="eventclass", order=8)
    escalateCount = schema.Int(title=u"Escalate Count", order=9) 
    
class IGraphInfo(IInfo):
    """
    Adapts GraphDefinition.
    """

class ITemplateFacade(IFacade):
    """
    A facade for monitoring templates.
    """

    def getTemplates():
        """
        Get all the monitoring templates in the system. This is used to fill
        out the tree view in the UI.
        """

    def addTemplate(id):
        """
        Add a new monitoring template to the dmd/Devices device class.
        """

    def deleteTemplate(uid):
        """
        Delete the monitoring template that is uniquely identified by the uid
        parameter.
        """

    def getDataSources(uid):
        """
        Return the data sources contained by the monitoring template uniquely
        identified by the uid parameter.
        """

    def getThresholds(uid):
        """
        Fetch the thresholds  contained by the monitoring template uniquely
        identified by the uid parameter.
        """

    def getThresholdTypes():
        """
        Get the available threshold types.  MinMaxThreshold comes from core,
        and the Holt Winters zenpack defines another type.  These are both
        subclasses of ThresholdClass.
        """

    def addThreshold(uid, thresholdType, thresholdId, dataPoints):
        """
        Add a threshold to the monitoring template uniquely identified by the
        uid parameter.
        """

    def removeThreshold(uid):
        """
        Delete the threshold uniquely identified by the uid parameter.
        """

    def getGraphs(uid):
        """
        Fetch the graph definitions associated with the monitoring template
        that is uniquely identified by the uid parameter.
        """

    def addDataPointToGraph(dataPointUid, graphUid):
        """
        Add data point to a graph.
        """

    def getCopyTargets(uid, query=''):
        """
        Get the device classes and devices that are candidates for having the
        monitoring template uniquely identified by uid copied to them. To be
        a viable target the object must not already have a template with the
        same ID defined on it, and the titleOrId must start with query
        (case-insensitvie match).
        """

    def copyTemplate(uid, targetUid):
        """
        Copy the monitoring template uniquely identified by the uid parameter
        to the device class or device uniquely identified by the targetUid
        parameter.
        """
