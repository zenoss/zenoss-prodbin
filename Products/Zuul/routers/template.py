###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
"""
Operations for Templates.

Available at:  /zport/dmd/template_router
"""

from Products import Zuul
from Products.ZenUtils.Ext import DirectResponse
from Products.Zuul.decorators import require
from Products.Zuul.form.interfaces import IFormBuilder
from Products.Zuul.routers import TreeRouter
from Products.ZenMessaging.actions import sendUserAction
from Products.ZenMessaging.actions.constants import ActionTargetType, ActionName


class TemplateRouter(TreeRouter):
    """
    A JSON/ExtDirect interface to operations on templates
    """

    def _getFacade(self):
        return Zuul.getFacade('template', self.context)

    def getTemplates(self, id):
        """
        Get all templates.

        @type  id: string
        @param id: not used
        @rtype:   [dictionary]
        @return:  List of objects representing the templates in tree hierarchy
        """
        facade = self._getFacade()
        templates = facade.getTemplates(id)
        data =  Zuul.marshal(templates)
        return data

    def getDeviceClassTemplates(self, id):
        """
        Get all templates by device class. This will return a tree where device
        classes are nodes, and templates are leaves.

        @type  id: string
        @param id: not used
        @rtype:   [dictionary]
        @return:  List of objects representing the templates in tree hierarchy
        """
        facade = self._getFacade()
        templates = facade.getTree(id)
        return [Zuul.marshal(templates)]

    def getAddTemplateTargets(self, query=None):
        """
        Get a list of available device classes where new templates can be added.

        @type  query: string
        @param query: not used
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects containing an available device
             class UID and a human-readable label for that class

        """
        facade = self._getFacade()
        data = facade.getAddTemplateTargets()
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def addTemplate(self, id, targetUid):
        """
        Add a template to a device class.

        @type  id: string
        @param id: Unique ID of the template to add
        @type  targetUid: string
        @param targetUid: Unique ID of the device class to add template to
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - nodeConfig: (dictionary) Object representing the added template
        """
        facade = self._getFacade()
        templateNode = facade.addTemplate(id, targetUid)
        if sendUserAction:
            sendUserAction(ActionTargetType.Template, ActionName.Add,
                           template=id, deviceclass=targetUid)
        return DirectResponse.succeed(nodeConfig=Zuul.marshal(templateNode))

    @require('Manage DMD')
    def deleteTemplate(self, uid):
        """
        Delete a template.

        @type  uid: string
        @param uid: Unique ID of the template to delete
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        facade.deleteTemplate(uid)
        msg = "Deleted node '%s'" % uid
        if sendUserAction:
            sendUserAction(ActionTargetType.Template, ActionName.Delete,
                           template=uid)
        return DirectResponse.succeed(msg=msg)

    @require('View')
    def getObjTemplates(self, uid):
        """
        @type  uid: string
        @param uid: Identifier for the object we want templates on, must descend from RRDView
        @rtype: DirectResponse
        @return: List of templates
        """
        facade = self._getFacade()
        templates = facade.getObjTemplates(uid)
        data = Zuul.marshal(templates)
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def makeLocalRRDTemplate(self, uid, templateName):
        """
        @type  uid: string
        @param uid: Identifer of the obj we wish to make the template local for
        @type  templateName: string
        @param templateName: identifier of the template
        """
        facade = self._getFacade()
        facade.makeLocalRRDTemplate(uid, templateName)
        if sendUserAction:
            sendUserAction(ActionTargetType.Template, 'MakeLocal',
                           template=templateName, target=uid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def removeLocalRRDTemplate(self, uid, templateName):
        """
        @type  uid: string
        @param uid: Identifer of the obj we wish to remove the local template
        @type  templateName: string
        @param templateName: identifier of the local template
        """
        facade = self._getFacade()
        facade.removeLocalRRDTemplate(uid, templateName)
        if sendUserAction:
            sendUserAction(ActionTargetType.Template, 'RemoveLocal',
                           template=templateName, target=uid)
        return DirectResponse.succeed()

    def getThresholds(self, uid, query=''):
        """
        Get the thresholds for a template.

        @type  uid: string
        @param uid: Unique ID of a template
        @type  query: string
        @param query: not used
        @rtype:   [dictionary]
        @return:  List of objects representing representing thresholds
        """
        facade = self._getFacade()
        thresholds = facade.getThresholds(uid)
        return DirectResponse.succeed(data=Zuul.marshal(thresholds))

    def getThresholdDetails(self, uid):
        """
        Get a threshold's details.

        @type  uid: string
        @param uid: Unique ID of a threshold
        @rtype:   dictionary
        @return:  B{Properties}:
             - record: (dictionary) Object representing the threshold
             - form: (dictionary) Object representing an ExtJS form for the threshold
        """
        facade = self._getFacade()
        thresholdDetails = facade.getThresholdDetails(uid)
        form = IFormBuilder(thresholdDetails).render(fieldsets=False)
        # turn the threshold into a dictionary
        data =  Zuul.marshal(dict(record=thresholdDetails, form=form))
        return data

    def getDataPoints(self, uid, query=''):
        """
        Get a list of available data points for a template.

        @type  query: string
        @param query: not used
        @type  uid: string
        @param uid: Unique ID of a template
        @rtype:   DirectResponse
        @return:  B{Properties}:
             - data: ([dictionary]) List of objects representing data points
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

    @require('Manage DMD')
    def addDataPoint(self, dataSourceUid, name):
        """
        Add a new data point to a data source.

        @type  dataSourceUid: string
        @param dataSourceUid: Unique ID of the data source to add data point to
        @type  name: string
        @param name: ID of the new data point
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        facade.addDataPoint(dataSourceUid, name)
        if sendUserAction:
            sendUserAction(ActionTargetType.DataPoint, ActionName.Add,
                           datapoint=name, datasource=dataSourceUid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def addDataSource(self, templateUid, name, type):
        """
        Add a new data source to a template.

        @type  templateUid: string
        @param templateUid: Unique ID of the template to add data source to
        @type  name: string
        @param name: ID of the new data source
        @type  type: string
        @param type: Type of the new data source. From getDataSourceTypes()
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        ds = facade.addDataSource(templateUid, name, type)
        if sendUserAction:
            sendUserAction(ActionTargetType.DataSource, ActionName.Add,
                           datasource=ds.getPrimaryId(), name=name,
                           dstype=type, template=templateUid)
        return DirectResponse.succeed()

    def getDataSources(self, uid):
        """
        Get the data sources for a template.

        @type  id: string
        @param id: Unique ID of a template
        @rtype:   [dictionary]
        @return:  List of objects representing representing data sources
        """
        facade = self._getFacade()
        dataSources = facade.getDataSources(uid)
        return DirectResponse.succeed(data=Zuul.marshal(dataSources))

    def getDataSourceDetails(self, uid):
        """
        Get a data source's details.

        @type  uid: string
        @param uid: Unique ID of a data source
        @rtype:   dictionary
        @return:  B{Properties}:
             - record: (dictionary) Object representing the data source
             - form: (dictionary) Object representing an ExtJS form for the data
             source
        """
        facade = self._getFacade()
        details = facade.getDataSourceDetails(uid)
        form = IFormBuilder(details).render()
        data =  Zuul.marshal(dict(record=details, form=form))
        return data

    def getDataPointDetails(self, uid):
        """
        Get a data point's details.

        @type  uid: string
        @param uid: Unique ID of a data point
        @rtype:   dictionary
        @return:  B{Properties}:
             - record: (dictionary) Object representing the data point
             - form: (dictionary) Object representing an ExtJS form for the data
             point
        """
        facade = self._getFacade()
        details = facade.getDataPointDetails(uid)
        form = IFormBuilder(details).render(fieldsets=False)
        data =  Zuul.marshal(dict(record=details, form=form))
        return data

    @require('Manage DMD')
    def setInfo(self, **data):
        """
        Set attributes on an object.
        This method accepts any keyword argument for the property that you wish
        to set. The only required property is "uid".

        @type    uid: string
        @keyword uid: Unique identifier of an object
        @rtype:  DirectResponse
        @return: B{Properties}:
            - data: (dictionary) The modified object
        """
        uid = data['uid']
        del data['uid']
        facade = self._getFacade()
        if sendUserAction:
            oldValues,newId = self._rememberOldInfoValues(uid, data)
        info = facade.setInfo(uid, data)
        if sendUserAction:
            self._sendSetInfoAction(uid, data, info, oldValues, newId)
        return DirectResponse.succeed(data=Zuul.marshal(info))

    def _rememberOldInfoValues(self, uid, data):
        # TODO: generalize this code for all object types, if possible.
        facade = self._getFacade()
        obj = facade._getObject(uid)
        oldInfo = facade._getDataSourceInfoFromObject(obj)
        oldValues = {}
        newId = None
        for key in data.keys():
            if key == 'newId':
                if oldInfo.id and data['newId'] and oldInfo.id != data['newId']:
                    newId = str(data['newId'])  # this entry gets deleted
            else:
                val = getattr(oldInfo, key, None)
                if val is not None:
                    oldValues[key] = str(val)  # unmutable copy
        return oldValues,newId

    def _sendSetInfoAction(self, uid, data, info, oldValues, newId):
        # Determine added, deleted, and changed values.
        #       Example: min=0, max=100, old_min=-100  [no old_max]
        # Otherwise we could just do:  sendUserAction(info.meta_type,
        #       ActionName.Edit, extra={info.meta_type:uid}, **data))
        type_ = info.meta_type
        extra = {type_:uid}
        if newId:
            extra['newId'] = newId  # old id can be determined from the uid
        for key in data.keys():
            newValue = getattr(info, key, None)
            hasNewValue = (newValue is not None)
            hasOldValue = (key in oldValues)
            newValueStr = str(newValue)
            oldValueStr = oldValues[key] if hasOldValue else None
            if hasNewValue and hasOldValue:
                if newValueStr != oldValueStr:
                    extra[key] = newValueStr
                    extra['old_'+key] = oldValueStr
            elif hasNewValue and not hasOldValue:
                extra[key] = newValueStr
            elif hasOldValue and not hasNewValue:
                extra['old_'+key] = oldValueStr
        sendUserAction(type_, ActionName.Edit, extra=extra)

    @require('Manage DMD')
    def addThreshold(self, **data):
        """
        Add a threshold.

        @type    uid: string
        @keyword uid: Unique identifier of template to add threshold to
        @type    thresholdType: string
        @keyword thresholdType: Type of the new threshold. From getThresholdTypes()
        @type    thresholdId: string
        @keyword thresholdId: ID of the new threshold
        @type    dataPoints: [string]
        @keyword dataPoints: List of data points to select for this threshold
        @rtype:  DirectResponse
        @return: Success message
        """
        uid = data['uid']
        thresholdType = data['thresholdType']
        thresholdId = data['thresholdId']
        dataPoints = data.get('dataPoints', None)
        facade = self._getFacade()
        facade.addThreshold(uid, thresholdType, thresholdId, dataPoints)
        if sendUserAction:
            sendUserAction(ActionTargetType.Threshold, ActionName.Add,
                           thresholdclass=thresholdId, template=uid,
                           thresholdtype=thresholdType, datapoints=dataPoints)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def removeThreshold(self, uid):
        """
        Remove a threshold.

        @type  uid: string
        @param uid: Unique identifier of threshold to remove
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.removeThreshold(uid)
        if sendUserAction:
            sendUserAction(ActionTargetType.Threshold, ActionName.Delete,
                           thresholdclass=uid)
        return DirectResponse.succeed()

    def getThresholdTypes(self, query=None):
        """
        Get a list of available threshold types.

        @type  query: string
        @param query: not used
        @rtype:   [dictionary]
        @return:  List of objects representing threshold types
        """
        facade = self._getFacade()
        data = facade.getThresholdTypes()
        return DirectResponse.succeed(data=data)

    def getDataSourceTypes(self, query):
        """
        Get a list of available data source types.

        @type  query: string
        @param query: not used
        @rtype:   [dictionary]
        @return:  List of objects representing data source types
        """
        facade = self._getFacade()
        data = facade.getDataSourceTypes()
        return DirectResponse.succeed(data=data)

    def getGraphs(self, uid, query=None):
        """
        Get the graph definitions for a template.

        @type  uid: string
        @param uid: Unique ID of a template
        @type  query: string
        @param query: not used
        @rtype:   [dictionary]
        @return:  List of objects representing representing graphs
        """
        facade = self._getFacade()
        graphs = facade.getGraphs(uid)
        return Zuul.marshal(graphs)

    @require('Manage DMD')
    def addDataPointToGraph(self, dataPointUid, graphUid, includeThresholds=False):
        """
        Add a data point to a graph.

        @type  dataPointUid: string
        @param dataPointUid: Unique ID of the data point to add to graph
        @type  graphUid: string
        @param graphUid: Unique ID of the graph to add data point to
        @type  includeThresholds: boolean
        @param includeThresholds: (optional) True to include related thresholds
                                  (default: False)
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        facade.addDataPointToGraph(dataPointUid, graphUid, includeThresholds)
        if sendUserAction:
            sendUserAction(ActionTargetType.Graph, 'AddDataPoint',
                           graph=graphUid, datapoint=dataPointUid,
                           includethresholds=includeThresholds)
        return DirectResponse.succeed()

    def getCopyTargets(self, uid, query=''):
        """
        Get a list of available device classes to copy a template to.

        @type  uid: string
        @param uid: Unique ID of the template to copy
        @type  query: string
        @param query: (optional) Filter the returned targets' names based on this
                      parameter (default: '')
        @rtype:   DirectResponse
        @return: B{Properties}:
            - data: ([dictionary]) List of objects containing an available device
             class UID and a human-readable label for that class
        """
        facade = self._getFacade()
        data = Zuul.marshal( facade.getCopyTargets(uid, query) )
        return DirectResponse.succeed(data=data)

    @require('Manage DMD')
    def copyTemplate(self, uid, targetUid):
        """
        Copy a template to a device or device class.

        @type  uid: string
        @param uid: Unique ID of the template to copy
        @type  targetUid: string
        @param targetUid: Unique ID of the device or device class to bind to template
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.copyTemplate(uid, targetUid)
        if sendUserAction:
            sendUserAction(ActionTargetType.Template, 'Copy',
                           template=uid, target=targetUid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def addGraphDefinition(self, templateUid, graphDefinitionId):
        """
        Add a new graph definition to a template.

        @type  templateUid: string
        @param templateUid: Unique ID of the template to add graph definition to
        @type  graphDefinitionId: string
        @param graphDefinitionId: ID of the new graph definition
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.addGraphDefinition(templateUid, graphDefinitionId)
        if sendUserAction:
            sendUserAction(ActionTargetType.GraphDefinition, ActionName.Add,
                           graphdefinition=graphDefinitionId,
                           template=templateUid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteDataSource(self, uid):
        """
        Delete a data source.

        @type  uid: string
        @param uid: Unique ID of the data source to delete
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.deleteDataSource(uid)
        if sendUserAction:
            sendUserAction(ActionTargetType.DataSource, ActionName.Delete,
                           datasource=uid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteDataPoint(self, uid):
        """
        Delete a data point.

        @type  uid: string
        @param uid: Unique ID of the data point to delete
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.deleteDataPoint(uid)
        if sendUserAction:
            sendUserAction(ActionTargetType.DataPoint, ActionName.Delete,
                           datapoint=uid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteGraphDefinition(self, uid):
        """
        Delete a graph definition.

        @type  uid: string
        @param uid: Unique ID of the graph definition to delete
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.deleteGraphDefinition(uid)
        if sendUserAction:
            sendUserAction(ActionTargetType.GraphDefinition, ActionName.Delete,
                           graphdefinition=uid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def deleteGraphPoint(self, uid):
        """
        Delete a graph point.

        @type  uid: string
        @param uid: Unique ID of the graph point to delete
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.deleteGraphPoint(uid)
        if sendUserAction:
            sendUserAction(ActionTargetType.GraphPoint, ActionName.Remove,
                           graphpoint=uid)
        return DirectResponse.succeed()

    def getGraphPoints(self, uid):
        """
        Get a list of graph points for a graph definition.

        @type  uid: string
        @param uid: Unique ID of a graph definition
        @rtype:  DirectResponse
        @return: B{Properties}:
            - data: ([dictionary]) List of objects representing graph points
        """
        facade = self._getFacade()
        graphPoints = facade.getGraphPoints(uid)
        return DirectResponse.succeed(data=Zuul.marshal(graphPoints))

    def getInfo(self, uid):
        """
        Get the properties of an object.

        @type  uid: string
        @param uid: Unique identifier of an object
        @rtype:   DirectResponse
        @return:  B{Properties}
            - data: (dictionary) Object properties
            - form: (dictionary) Object representing an ExtJS form for the object
        """
        facade = self._getFacade()
        info = facade.getInfo(uid)
        form = IFormBuilder(info).render(fieldsets=False)
        return DirectResponse(success=True, data=Zuul.marshal(info), form=form)

    @require('Manage DMD')
    def addThresholdToGraph(self, graphUid, thresholdUid):
        """
        Add a threshold to a graph definition.

        @type  graphUid: string
        @param graphUid: Unique ID of the graph definition to add threshold to
        @type  thresholdUid: string
        @param thresholdUid: Unique ID of the threshold to add
        @rtype:   DirectResponse
        @return:  Success message
        """
        facade = self._getFacade()
        facade.addThresholdToGraph(graphUid, thresholdUid)
        if sendUserAction:
            sendUserAction(ActionTargetType.Graph, 'AddThreshold',
                           graph=graphUid, thresholdclass=thresholdUid)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def addCustomToGraph(self, graphUid, customId, customType):
        """
        Add a custom graph point to a graph definition.

        @type  graphUid: string
        @param graphUid: Unique ID of the graph definition to add graph point to
        @type  customId: string
        @param customId: ID of the new custom graph point
        @type  customType: string
        @param customType: Type of the new graph point. From getGraphInstructionTypes()
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.addCustomToGraph(graphUid, customId, customType)
        if sendUserAction:
            sendUserAction(ActionTargetType.Graph, 'AddCustomGraphPoint',
                           custom=customId, graph=graphUid)
        return DirectResponse.succeed()

    def getGraphInstructionTypes(self, query=''):
        """
        Get a list of available instruction types for graph points.

        @type  query: string
        @param query: not used
        @rtype:   DirectResponse
        @return: B{Properties}:
            - data: ([dictionary]) List of objects representing instruction types
        """
        facade = self._getFacade()
        types = facade.getGraphInstructionTypes()
        return DirectResponse.succeed(data=Zuul.marshal(types))

    @require('Manage DMD')
    def setGraphPointSequence(self, uids):
        """
        Sets the sequence of graph points in a graph definition.

        @type  uids: [string]
        @param uids: List of graph point UID's in desired order
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade.setGraphPointSequence(uids)
        if sendUserAction:
            # TODO: Is it enforced that they're all in the same graph definition?
            #       If so:  graphdefinition=/blah/uid sequence=[one,two,three]
            sendUserAction(ActionTargetType.GraphDefinition,
                           'SetGraphPointSequence',
                           sequence=uids)
        return DirectResponse.succeed()

    def getGraphDefinition(self, uid):
        """
        Get a graph definition.

        @type  uid: string
        @param uid: Unique ID of the graph definition to retrieve
        @rtype:   DirectResponse
        @return: B{Properties}:
            - data: (dictionary) Object representing a graph definition
        """
        facade = self._getFacade()
        graphDef = facade.getGraphDefinition(uid)
        return DirectResponse.succeed(data=Zuul.marshal(graphDef))

    @require('Manage DMD')
    def setGraphDefinition(self, **data):
        """
        Set attributes on an graph definition.
        This method accepts any keyword argument for the property that you wish
        to set. Properties are enumerated via getGraphDefinition(). The only
        required property is "uid".

        @type    uid: string
        @keyword uid: Unique identifier of an object
        @rtype:  DirectResponse
        @return: B{Properties}:
            - data: (dictionary) The modified object
        """
        uid = data['uid']
        del data['uid']
        for int_attr in ('miny', 'maxy'):
            try:
                x = int(data[int_attr])
            except (ValueError, KeyError):
                x = -1
            data[int_attr] = x
        if sendUserAction:
            oldValues,newId = self._rememberOldInfoValues(uid, data)
        facade = self._getFacade()
        info = facade.setInfo(uid, data)
        if sendUserAction:
            self._sendSetInfoAction(uid, data, info, oldValues, newId)
        return DirectResponse.succeed()

    @require('Manage DMD')
    def setGraphDefinitionSequence(self, uids):
        """
        Sets the sequence of graph definitions.

        @type  uids: [string]
        @param uids: List of graph definition UID's in desired order
        @rtype:  DirectResponse
        @return: Success message
        """
        facade = self._getFacade()
        facade._setGraphDefinitionSequence(uids)
        if sendUserAction:
            # TODO: Is it enforced that they're all in the same template?
            #       If so:  template=/blah/uid sequence=[one,two,three]
            sendUserAction(ActionTargetType.Template,
                           'SetGraphDefinitionSequence',
                           sequence=uids)
        return DirectResponse.succeed()
