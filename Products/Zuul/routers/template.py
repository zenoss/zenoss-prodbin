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

class TemplateRouter(DirectRouter):

    def _getFacade(self):
        return Zuul.getFacade('template')

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

    def getDataSources(self, id):
        """
        Get the data sources for the RRD template identified by uid.
        """
        facade = self._getFacade()
        dataSources = facade.getDataSources(id)
        return Zuul.marshal(dataSources)

    def getThresholds(self, uid):
        """
        Get the thresholds for the RRD template identified by uid.
        """
        facade = self._getFacade()
        thresholds = facade.getThresholds(uid)
        return Zuul.marshal(thresholds)

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

    def getGraphs(self, uid):
        """
        Get the graphs for the RRD template identified by uid.
        """
        facade = self._getFacade()
        graphs = facade.getGraphs(uid)
        return Zuul.marshal(graphs)
