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

import logging
from itertools import imap
from Acquisition import aq_parent
from Products.ZenUtils.Utils import prepId
from Products.Zuul.interfaces import ICatalogTool
from Products.Zuul.interfaces import ITemplateNode
from Products.Zuul.interfaces import ITemplateLeaf
from Products.Zuul.interfaces import IDataSourceInfo
from Products.Zuul.interfaces import IDataPointInfo
from Products.Zuul.interfaces import IThresholdInfo
from Products.Zuul.interfaces import IGraphInfo
from Products.Zuul.utils import unbrain, severityId
from Products.Zuul.facades import ZuulFacade
from Products.ZenModel.RRDTemplate import RRDTemplate
from Products.ZenModel.RRDDataSource import RRDDataSource
from Products.ZenModel.RRDDataPoint import RRDDataPoint
from Products.ZenModel.ThresholdClass import ThresholdClass
from Products.ZenModel.GraphDefinition import GraphDefinition

log = logging.getLogger('zen.TemplateFacade')

class TemplateFacade(ZuulFacade):

    def getTemplates(self):
        catalog = self._getCatalog('/zport/dmd/Devices')
        brains = catalog.search(types=RRDTemplate)
        templates = imap(unbrain, brains)
        nodes = {}
        for template in templates:
            if template.id not in nodes:
                nodes[template.id] = ITemplateNode(template)
            leaf = ITemplateLeaf(template)
            nodes[template.id]._addChild(leaf)
        for key in sorted(nodes.keys(), key=str.lower):
            yield nodes[key]        

    def addTemplate(self, id):
        id = prepId(id)
        relationship = self._dmd.Devices.rrdTemplates
        relationship._setObject(id, RRDTemplate(id))
        template = getattr(relationship, id)
        node = ITemplateNode(template)
        leaf = ITemplateLeaf(template)
        node._addChild(leaf)
        return node
    
    def _deleteObject(self, uid):
        """ Deletes the object by getting the parent
        and then calling delete on the objects id.
        @param string uid Must be a valid path
        """
        obj = self._getObject(uid)
        context = aq_parent(obj)
        context._delObject(obj.id)
        
    def deleteTemplate(self, uid):
        return self._deleteObject(uid)

    def getDataSources(self, uid):
        catalog = self._getCatalog(uid)
        if isinstance(catalog.context, RRDTemplate):
            brains = catalog.search(types=RRDDataSource)
            dataSources = imap(unbrain, brains)
            infos = imap(IDataSourceInfo, dataSources)
        else:
            brains = catalog.search(types=RRDDataPoint)
            dataPoints = imap(unbrain, brains)
            infos = imap(IDataPointInfo, dataPoints)
        return infos

    def getThresholds(self, uid):
        catalog = self._getCatalog(uid)
        brains = catalog.search(types=ThresholdClass)
        thresholds = imap(unbrain, brains)
        return imap(IThresholdInfo, thresholds)
    
    def getThresholdDetails(self, uid):
        """
        @param String uid: the id of the threshold
        """
        threshold = self._getObject(uid)
        template = threshold.rrdTemplate()
        info = IThresholdInfo(threshold)
        # don't show the "selected one" in the list of avaialble
        info.allDataPoints = [point for point in template.getRRDDataPointNames() if not point in info.dataPoints]
        return info
    
    def getThresholdTypes(self):
        data = []
        template = self._dmd.Devices.rrdTemplates.Device
        for pythonClass, type in template.getThresholdClasses():
            data.append({'type': type})
        return data

    def addThreshold(self, uid, thresholdType, thresholdId, dataPoints):
        thresholdId = prepId(thresholdId)
        template = self._getObject(uid)
        thresholds = template.thresholds
        for pythonClass, key in template.getThresholdClasses():
            if key == thresholdType:
                thresholds._setObject(thresholdId, pythonClass(thresholdId))
                break
        else:
            raise Exception('Unknow threshold type: %s' % thresholdType)
        threshold = getattr(thresholds, thresholdId)
        dsnames = self._translateDataPoints(dataPoints)
        threshold._updateProperty('dsnames', dsnames)
                                                                        
    def _translateDataPoints(self, dataPoints):
        """ Takes the list of datapoints from te server
        and turns them into the proper dsnames that the
        threshold items expects
        @param List dataPointsUids
        @return List proper names from the dataPoint object
        """
        dsnames = []
        for dataPointUid in dataPoints:
            dataPoint = self._getObject(dataPointUid)
            dsnames.append( dataPoint.name() )
        return dsnames
            
    def editThreshold(self, uid, data):
        """
        Takes a uid of a threshold and a dictionary of
        {property: value}. This method then attempts to apply each
        property to the threshold. If the property doesn't
        exit it is ignored.
        @param String UID of the Threshold
        @param Dictionary data 
        @return IThresholdInfo
        """
        threshold = self._getObject(uid)
        info = IThresholdInfo(threshold)
                
        for key in data.keys():
            if hasattr(info, key):
                setattr(info, key, data[key])
                
        return info
        
    def removeThreshold(self, uid):
        """Removes the threshold
        @param string uid
        """
        return self._deleteObject(uid)
    
    def getGraphs(self, uid):
        catalog = self._getCatalog(uid)
        brains = catalog.search(types=GraphDefinition)
        graphs = imap(unbrain, brains)
        return imap(IGraphInfo, graphs)

    def addDataPointToGraph(self, dataPointUid, graphUid):
        dataPoint = self._getObject(dataPointUid)
        graph = self._getObject(graphUid)
        graph.manage_addDataPointGraphPoints([dataPoint.name()])

    def _getCatalog(self, uid):
        obj = self._getObject(uid)
        return ICatalogTool(obj)
