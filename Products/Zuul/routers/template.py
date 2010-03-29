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

from Products.ZenUtils.Ext import DirectRouter
from Products import Zuul
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
        result = {}
        try:
            facade = self._getFacade()
            templateNode = facade.addTemplate(id) 
            result['nodeConfig'] = Zuul.marshal(templateNode)
            result['success'] = True
        except Exception, e:
            result['msg'] = str(e)
            result['success'] = False
        return result

    @require('Manage DMD')
    def deleteTemplate(self, uid):
        facade = self._getFacade()
        facade.deleteTemplate(uid)
        msg = "Deleted node '%s'" % uid
        return {'success': True, 'msg': msg}

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

    def addDataPoint(self, dataSourceUid, name):
        """
        Given a datasource uid and a name, this creates a new datapoint
        """
        facade = self._getFacade()
        facade.addDataPoint(dataSourceUid, name)
        return {'success': True}
    
    def addDataSource(self, templateUid, name, type):
        """
        Adds a new datasource designated by "name" to the template path
        specified by the templateUid
        """
        facade = self._getFacade()
        facade.addDataSource(templateUid, name, type)
        return {'success': True}
        
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
        form = IFormBuilder(details).render(fieldsets=False)
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
        data['enabled'] = data.has_key('enabled')
        facade = self._getFacade()
        facade.setInfo(uid, data)
        return {'success': True}
                
    @require('Manage DMD')
    def addThreshold(self, uid, thresholdType, thresholdId, dataPoints):
        facade = self._getFacade()
        facade.addThreshold(uid, thresholdType, thresholdId, dataPoints)
        return {'success': True}

    @require('Manage DMD')
    def removeThreshold(self, uid):
        """Gets a list of Uids from the server, and deletes each one. 
        """
        facade = self._getFacade()
        facade.removeThreshold(uid)
        return {'success': True}
    
    def getThresholdTypes(self, query):
        facade = self._getFacade()
        data = facade.getThresholdTypes()
        return {'success': True, 'data': data}

    def getDataSourceTypes(self, query):
        facade = self._getFacade()
        data = facade.getDataSourceTypes()
        return {'success': True, 'data': data}

    def getGraphs(self, uid, query=None):
        """
        Get the graphs for the RRD  identified by uid.
        """
        facade = self._getFacade()
        graphs = facade.getGraphs(uid)
        return Zuul.marshal(graphs)

    @require('Manage DMD')
    def addDataPointToGraph(self, dataPointUid, graphUid):
        """
        Add a datapoint to a graph.
        """
        facade = self._getFacade()
        facade.addDataPointToGraph(dataPointUid, graphUid)
        return {'success': True}

    def getCopyTargets(self, uid, query=''):
        """
        Get device classes and devices that do not already have a local copy
        of the RRDTemplate uniquely identified by the uid parameter.
        """
        facade = self._getFacade()
        data = Zuul.marshal( facade.getCopyTargets(uid, query) )
        return {'success': True, 'data': data}

    def copyTemplate(self, uid, targetUid):
        """
        Copy template to device or device class uniquely identified by
        targetUid
        """
        facade = self._getFacade()
        facade.copyTemplate(uid, targetUid)
        return {'success': True}

    @require('Manage DMD')
    def addGraphDefinition(self, templateUid, graphDefinitionId):
        facade = self._getFacade()
        facade.addGraphDefinition(templateUid, graphDefinitionId)
        return {'success': True}

    @require('Manage DMD')
    def deleteGraphDefinition(self, uid):
        facade = self._getFacade()
        facade.deleteGraphDefinition(uid)
        return {'success': True}

    def getGraphPoints(self, uid):
        facade = self._getFacade()
        graphPoints = facade.getGraphPoints(uid)
        return {'success': True,
                'data': Zuul.marshal(graphPoints)
                }

    @require('Manage DMD')
    def addThresholdToGraph(self, graphUid, thresholdUid):
        facade = self._getFacade()
        facade.addThresholdToGraph(graphUid, thresholdUid)
        return {'success': True}

    @require('Manage DMD')
    def setGraphPointSequence(self, uids):
        facade = self._getFacade()
        facade.setGraphPointSequence(uids)
        return {'success': True}
