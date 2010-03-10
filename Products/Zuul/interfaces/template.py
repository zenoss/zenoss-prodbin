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

class IDataPointInfo(IInfo):
    """
    Adapts RRDDataPoint.
    """

class IThresholdInfo(IInfo):
    """
    Adapts ThresholdClass.
    """

class IMinMaxThresholdInfo(IThresholdInfo):
    """
    Adapts the MinMaxThresholdClass
    """
    
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
