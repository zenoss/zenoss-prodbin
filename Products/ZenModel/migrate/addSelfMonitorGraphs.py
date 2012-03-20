###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import logging
import Migrate
import Globals
from Products.ZenModel.SelfMonitoring import SelfMonitoring
from Products.ZenModel import RRDTemplate
from Products.ZenModel.RRDDataSource import RRDDataSource
from Products.ZenModel.BuiltInDS import BuiltInDS

_LOG = logging.getLogger("zen.migrate")

_SELF_MONITORING_ID = 'selfMonitoring'
_ZENOSS_TEMPLATE_ID = 'zenossTemplate'
_ZENOSS_DATASOURCE_ID = 'default'


def addDpIfMissing(ds, dpName):
    pass

class AddSelfMonitorGraphs(Migrate.Step):
    
    version = Migrate.Version(4, 2, 0)
   
    def cutover(self, dmd):
        selfMonitoring = dmd._getOb(_SELF_MONITORING_ID, None)
        if selfMonitoring is None:
            _LOG.info("Adding self monitoring graphs.")
            selfMonitoring = SelfMonitoring(_SELF_MONITORING_ID)
            dmd._setObject(selfMonitoring.id, selfMonitoring)
            selfMonitoring = dmd._getOb(_SELF_MONITORING_ID)

        zenossTemplate = selfMonitoring._getOb(_ZENOSS_TEMPLATE_ID, None)
        if zenossTemplate is None:
            _LOG.info("Adding default zenossTemplate.")
            RRDTemplate.manage_addRRDTemplate(selfMonitoring, _ZENOSS_TEMPLATE_ID)
            zenossTemplate = selfMonitoring._getOb(_ZENOSS_TEMPLATE_ID)

        # ZODB data source
        try:
            zodbDs = zenossTemplate.datasources.zodb
        except AttributeError:
            zodbDs = zenossTemplate.manage_addRRDDataSource('zodb', 'BuiltInDS.Built-In')

        try:
            globalCatalogObjectCount = zodbDs.datasources.globalCatalogObjectCount
        except AttributeError:
            globalCatalogObjectCount = zodbDs.manage_addRRDDataPoint('globalCatalogObjectCount')
        if globalCatalogObjectCount.rrdtype != 'GAUGE': globalCatalogObjectCount.rrdtype = 'GAUGE'

        try:
            zodbObjectCount = zodbDs.datasources.globalCatalogObjectCount
        except AttributeError:
            zodbObjectCount = zodbDs.manage_addRRDDataPoint('zodbObjectCount')
        if zodbObjectCount.rrdtype != 'GAUGE': zodbObjectCount.rrdtype = 'GAUGE'

        try:
            zodbSize = zodbDs.datasources.zodbSize
        except AttributeError:
            zodbSize = zodbDs.manage_addRRDDataPoint('zodbSize')
        if zodbSize.rrdtype != 'GAUGE': zodbObjectCount.rrdtype = 'GAUGE'

        try:
            zodbGraphDef = zenossTemplate.graphDefs.zodbCount
        except AttributeError:
            zodbGraphDef = zenossTemplate.manage_addGraphDefinition('zodbCount')
            zodbGraphDef.manage_addDataPointGraphPoints(['zodb_zodbObjectCount',])

        try:
            zodbGraphDef = zenossTemplate.graphDefs.catalogCount
        except AttributeError:
            zodbGraphDef = zenossTemplate.manage_addGraphDefinition('catalogCount')
            zodbGraphDef.manage_addDataPointGraphPoints(['zodb_globalCatalogObjectCount',])

        try:
            zodbGraphDef = zenossTemplate.graphDefs.zodbSize
        except AttributeError:
            zodbGraphDef = zenossTemplate.manage_addGraphDefinition('zodbSize')
            zodbGraphDef.units = 'bytes'
            zodbGraphDef.manage_addDataPointGraphPoints(['zodb_zodbSize',])

AddSelfMonitorGraphs()
