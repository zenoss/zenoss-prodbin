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

from Products import Zuul
from Products.ZenUtils.Ext import DirectRouter, DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.form.interfaces import IFormBuilder

class TemplateRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('template', self.context)

    def getTemplates(self, id):
        """
        Get the templates throughout the device class hierarchy defined by
        uid.
        """
        facade = self._getFacade()
        templates = facade.getTemplates()
        return Zuul.marshal(templates)

    @require('Manage DMD')
    def addTemplate(self, id):
        """
        Add a template to dmd/Devices.
        """
        result = None
        try:
            facade = self._getFacade()
            templateNode = facade.addTemplate(id)
            result = DirectResponse.succeed(
                nodeConfig=Zuul.marshal(templateNode))
        except Exception, e:
            result = DirectResponse.fail(msg=str(e))
        return result

    @require('Manage DMD')
    def deleteTemplate(self, uid):
        facade = self._getFacade()
        facade.deleteTemplate(uid)
        msg = "Deleted node '%s'" % uid
        return DirectResponse.succeed(msg=msg)

    def getThresholds(self, uid, query=''):
        """
        Get the thresholds for the RRD template identified by uid.
        """
        facade = self._getFacade()
        thresholds = facade.getThresholds(uid)
        return Zuul.marshal(thresholds)

    def getThresholdDetails(self, uid):
        """
        Returns everything needed for the threshold dialog
        """
        facade = self._getFacade()
        thresholdDetails = facade.getThresholdDetails(uid)
        form = IFormBuilder(thresholdDetails).render(fieldsets=False)
        # turn the threshold into a dictionary
        data =  Zuul.marshal(dict(record=thresholdDetails, form=form))
        return data

    def getDataPoints(self, query, uid):
        """
        @returns [DataPointInfo] Given a template UID, this returns
        every data point associated with it
        """
        datapoints = []
        facade = self._getFacade()
        # go through each of our datasources and get all the data points
        datasources = facade.getDataSources(uid)
        for datasource in datasources:
            for datapoint in facade.getDataSources(datasource.uid):
                datapoints.append(datapoint)
        data = Zuul.marshal(datapoints)
        return DirectResponse.succeed(data=data)
    
    def addDataPoint(self, dataSourceUid, name):
        """
        Given a datasource uid and a name, this creates a new datapoint
        """
        facade = self._getFacade()
        facade.addDataPoint(dataSourceUid, name)
        return DirectResponse.succeed()

    def addDataSource(self, templateUid, name, type):
        """
        Adds a new datasource designated by "name" to the template path
        specified by the templateUid
        """
        facade = self._getFacade()
        facade.addDataSource(templateUid, name, type)
        return DirectResponse.succeed()

    def getDataSources(self, id):
        """
        Get the data sources for the RRD template identified by uid.
        """
        facade = self._getFacade()
        dataSources = facade.getDataSources(id)
        return Zuul.marshal(dataSources)

    def getDataSourceDetails(self, uid):
        """
        Returns everything we need for the Edit DataSources Dialog
        """
        facade = self._getFacade()
        details = facade.getDataSourceDetails(uid)
        form = IFormBuilder(details).render()
        data =  Zuul.marshal(dict(record=details, form=form))
        return data

    def getDataPointDetails(self, uid):
        """
        Returns everything we need for the Edit DataSources Dialog
        """
        facade = self._getFacade()
        details = facade.getDataPointDetails(uid)
        form = IFormBuilder(details).render(fieldsets=False)
        data =  Zuul.marshal(dict(record=details, form=form))
        return data

    @require('Manage DMD')
    def setInfo(self, **data):
        uid = data['uid']
        del data['uid']
        facade = self._getFacade()
        facade.setInfo(uid, data)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def addThreshold(self, **data):
        uid = data['uid']
        thresholdType = data['thresholdType']
        thresholdId = data['thresholdId']
        dataPoints = data.get('dataPoints', None)
        facade = self._getFacade()
        facade.addThreshold(uid, thresholdType, thresholdId, dataPoints)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def removeThreshold(self, uid):
        """Gets a list of Uids from the server, and deletes each one.
        """
        facade = self._getFacade()
        facade.removeThreshold(uid)
        return DirectResponse.succeed()

    def getThresholdTypes(self, query):
        facade = self._getFacade()
        data = facade.getThresholdTypes()
        return DirectResponse.succeed(data=data) 

    def getDataSourceTypes(self, query):
        facade = self._getFacade()
        data = facade.getDataSourceTypes()
        return DirectResponse.succeed(data=data) 

    def getGraphs(self, uid, query=None):
        """
        Get the graphs for the RRD  identified by uid.
        """
        facade = self._getFacade()
        graphs = facade.getGraphs(uid)
        return Zuul.marshal(graphs)

    @require('Manage DMD')
    def addDataPointToGraph(self, dataPointUid, graphUid, includeThresholds=False):
        """
        Add a datapoint to a graph.
        """
        facade = self._getFacade()
        facade.addDataPointToGraph(dataPointUid, graphUid, includeThresholds)
        return DirectResponse.succeed()

    def getCopyTargets(self, uid, query=''):
        """
        Get device classes and devices that do not already have a local copy
        of the RRDTemplate uniquely identified by the uid parameter.
        """
        facade = self._getFacade()
        data = Zuul.marshal( facade.getCopyTargets(uid, query) )
        return DirectResponse.succeed(data=data)

    def copyTemplate(self, uid, targetUid):
        """
        Copy template to device or device class uniquely identified by
        targetUid
        """
        facade = self._getFacade()
        facade.copyTemplate(uid, targetUid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def addGraphDefinition(self, templateUid, graphDefinitionId):
        facade = self._getFacade()
        facade.addGraphDefinition(templateUid, graphDefinitionId)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteDataSource(self, uid):
        facade = self._getFacade()
        facade.deleteDataSource(uid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteDataPoint(self, uid):
        facade = self._getFacade()
        facade.deleteDataPoint(uid)
        return DirectResponse.succeed()
    
    @require('Manage DMD')
    def deleteGraphDefinition(self, uid):
        facade = self._getFacade()
        facade.deleteGraphDefinition(uid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteGraphPoint(self, uid):
        facade = self._getFacade()
        facade.deleteGraphPoint(uid)
        return DirectResponse.succeed()

    def getGraphPoints(self, uid):
        facade = self._getFacade()
        graphPoints = facade.getGraphPoints(uid)
        return DirectResponse.succeed(data=Zuul.marshal(graphPoints))

    def getInfo(self, uid):
        """
        @returns the details of a single info object as well as the form describing its schema
        """
        facade = self._getFacade()
        info = facade.getInfo(uid)
        form = IFormBuilder(info).render(fieldsets=False)
        return DirectResponse(success=True, data=Zuul.marshal(info), form=form)

    @require('Manage DMD')
    def addThresholdToGraph(self, graphUid, thresholdUid):
        facade = self._getFacade()
        facade.addThresholdToGraph(graphUid, thresholdUid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def addCustomToGraph(self, graphUid, customId, customType):
        facade = self._getFacade()
        facade.addCustomToGraph(graphUid, customId, customType)
        return DirectResponse.succeed()

    def getGraphInstructionTypes(self, query=''):
        facade = self._getFacade()
        types = facade.getGraphInstructionTypes()
        return DirectResponse.succeed(data=Zuul.marshal(types))

    @require('Manage DMD')
    def setGraphPointSequence(self, uids):
        facade = self._getFacade()
        facade.setGraphPointSequence(uids)
        return DirectResponse.succeed()

    def getGraphDefinition(self, uid):
        facade = self._getFacade()
        graphDef = facade.getGraphDefinition(uid)
        return DirectResponse.succeed(data=Zuul.marshal(graphDef))

    @require('Manage DMD')
    def setGraphDefinition(self, **data):
        uid = data['uid']
        del data['uid']
        data['log'] = 'log' in data
        data['base'] = 'base' in data
        data['hasSummary'] = 'hasSummary' in data
        facade = self._getFacade()
        facade.setInfo(uid, data)
        return DirectResponse.succeed()
        
    @require('Manage DMD')
    def setGraphDefinitionSequence(self, uids):
        facade = self._getFacade()
        facade._setGraphDefinitionSequence(uids)
        return DirectResponse.succeed()
