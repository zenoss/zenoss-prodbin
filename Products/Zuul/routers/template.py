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

    @require('View')
    def getTemplates(self, id):
        """
        Get the templates throughout the device class hierarchy defined by
        uid.
        """
        facade = self._getFacade()
        templates = facade.getTemplates()
        return Zuul.marshal(templates)

    @require('View')
    def getDataSources(self, id):
        """
        Get the data sources for the RRD template identified by uid.
        """
        facade = self._getFacade()
        dataSources = facade.getDataSources(id)
        return Zuul.marshal(dataSources)

    @require('View')
    def getThresholds(self, uid):
        """
        Get the thresholds for the RRD template identified by uid.
        """
        facade = self._getFacade()
        thresholds = facade.getThresholds(uid)
        return Zuul.marshal(thresholds)

    @require('View')
    def getGraphs(self, uid):
        """
        Get the graphs for the RRD template identified by uid.
        """
        facade = self._getFacade()
        graphs = facade.getGraphs(uid)
        return Zuul.marshal(graphs)
