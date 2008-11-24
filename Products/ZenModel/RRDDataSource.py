###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""RRDDataSource

Base class for DataSources
"""

import os

from DateTime import DateTime
from AccessControl import ClassSecurityInfo, Permissions

from Products.PageTemplates.Expressions import getEngine

from Products.ZenUtils.ZenTales import talesCompile
from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable


def manage_addRRDDataSource(context, id, dsOption, REQUEST = None):
   """make a RRDDataSource"""
   ds = context.getDataSourceInstance(id, dsOption, REQUEST=None)
   context._setObject(ds.id, ds)
   if REQUEST is not None:
       REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

class RRDDataSource(ZenModelRM, ZenPackable):

    meta_type = 'RRDDataSource'

    paramtypes = ('integer', 'string', 'float')
    sourcetypes = ()
    
    sourcetype = None
    enabled = True
    component = ''
    eventClass = ''
    eventKey = ''
    severity = 3
    commandTemplate = ""
    cycletime = 300

    _properties = (
        {'id':'sourcetype', 'type':'selection',
        'select_variable' : 'sourcetypes', 'mode':'w'},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'component', 'type':'string', 'mode':'w'},
        {'id':'eventClass', 'type':'string', 'mode':'w'},
        {'id':'eventKey', 'type':'string', 'mode':'w'},
        {'id':'severity', 'type':'int', 'mode':'w'},
        {'id':'commandTemplate', 'type':'string', 'mode':'w'},
        {'id':'cycletime', 'type':'int', 'mode':'w'},
        )

    _relations = ZenPackable._relations + (
        ("rrdTemplate", ToOne(ToManyCont,"Products.ZenModel.RRDTemplate","datasources")),
        ("datapoints", ToManyCont(ToOne,"Products.ZenModel.RRDDataPoint","datasource")),
        )
    
    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editRRDDataSource',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Data Source'
            , 'action'        : 'editRRDDataSource'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    
    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        from RRDTemplate import crumbspath
        crumbs = super(RRDDataSource, self).breadCrumbs(terminator)
        return crumbspath(self.rrdTemplate(), crumbs, -2)


    def getDescription(self):
        return None


    def getRRDDataPoints(self):
        return self.datapoints()
        
        
    def useZenCommand(self):
        return False


    def manage_addRRDDataPoint(self, id, REQUEST = None):
        """make a RRDDataPoint"""
        if not id:
            return self.callZenScreen(REQUEST)
        from Products.ZenModel.RRDDataPoint import RRDDataPoint
        dp = RRDDataPoint(id)
        self.datapoints._setObject(dp.id, dp)
        dp = self.datapoints._getOb(dp.id)
        if REQUEST:
            if dp:
                #REQUEST['message'] = "Command Added"
                url = '%s/datapoints/%s' % (self.getPrimaryUrlPath(), dp.id)
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return dp


    def manage_deleteRRDDataPoints(self, ids=(), REQUEST=None):
        """Delete RRDDataPoints from this RRDDataSource"""

        def clean(rel, id):
            for obj in rel():
                if id in obj.dsnames:
                    obj.dsnames.remove(id)
                    if not obj.dsnames:
                        rel._delObject(obj.id)

        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            dp = getattr(self.datapoints,id,False)
            if dp:
                if getattr(self, 'device', False):
                    perfConf = self.device().getPerformanceServer()
                    perfConf.deleteRRDFiles(device=self.device().id, datapoint=dp.name())
                else:
                    for d in self.deviceClass.obj.getSubDevicesGen():
                        perfConf = d.getPerformanceServer()
                        perfConf.deleteRRDFiles(device=d.id, datapoint=dp.name())
        
                clean(self.graphs, dp.name())
                clean(self.thresholds, dp.name())
                self.datapoints._delObject(dp.id)
                
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    #security.declareProtected('Manage DMD', 'manage_addDataPointsToGraphs')
    def manage_addDataPointsToGraphs(self, ids=(), graphIds=(), REQUEST=None):
        """
        Create GraphPoints for all datapoints given datapoints (ids)
        in each of the graphDefs (graphIds.)
        If a graphpoint already exists for a datapoint in a graphDef then
        don't create a 2nd one.
        """
        newGps = []
        for graphDefId in graphIds:
            graphDef = self.rrdTemplate.graphDefs._getOb(graphDefId, None)
            if graphDef:
                for dpId in ids:
                    dp = self.datapoints._getOb(dpId, None)
                    if dp and not graphDef.isDataPointGraphed(dp.name()):
                        newGps += graphDef.manage_addDataPointGraphPoints(
                                                                [dp.name()])
        if REQUEST:
            numNew = len(newGps)
            REQUEST['message'] = '%s GraphPoint%s added' % (
                        numNew, numNew != 1 and 's' or '')
            return self.callZenScreen(REQUEST)
        return newGps


    def getCommand(self, context, cmd=None):
        """Return localized command target.
        """
        # Perform a TALES eval on the expression using self
        if cmd is None:
            cmd = self.commandTemplate
        if not cmd.startswith('string:') and not cmd.startswith('python:'):
            cmd = 'string:%s' % cmd
        compiled = talesCompile(cmd)
        d = context.device()
        environ = {'dev' : d,
                   'device': d,
                   'devname': d.id,
                   'here' : context, 
                   'zCommandPath' : context.zCommandPath,
                   'nothing' : None,
                   'now' : DateTime() }
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        res = self.checkCommandPrefix(context, res)
        return res
        

    def getComponent(self, context, component=None):
        """Return localized component.
        """
        if component is None:
            component = self.component
        if not component.startswith('string:') and \
                not component.startswith('python:'):
            component = 'string:%s' % component
        compiled = talesCompile(component)
        d = context.device()
        environ = {'dev' : d,
                   'device': d,
                   'devname': d.id,
                   'here' : context, 
                   'nothing' : None,
                   'now' : DateTime() }
        res = compiled(getEngine().getContext(environ))
        if isinstance(res, Exception):
            raise res
        return res


    def checkCommandPrefix(self, context, cmd):
        if not cmd.startswith('/') and not cmd.startswith('$'):
            if not cmd.startswith(context.zCommandPath):
                cmd = os.path.join(context.zCommandPath, cmd)
        return cmd


    def getSeverityString(self):
        return self.ZenEventManager.getSeverityString(self.severity)


    def zmanage_editProperties(self, REQUEST=None, ignored=None):
        return ZenModelRM.zmanage_editProperties(self, REQUEST)


class SimpleRRDDataSource(RRDDataSource):
    """
    A SimpleRRDDataSource has a single datapoint that shares the name of the 
    data source.
    """
    
    def addDataPoints(self):
        """
        Make sure there is exactly one datapoint and that it has the same name
        as the datasource.
        """
        dpid = self.prepId(self.id)
        remove = [d for d in self.datapoints() if d.id != dpid]
        for dp in remove:
            self.datapoints._delObject(dp.id)
        if not self.datapoints._getOb(dpid, None):
            self.manage_addRRDDataPoint(dpid)
    
    def zmanage_editProperties(self, REQUEST=None):
        """
        Overrides the method defined in RRDDataSource. Called when user clicks
        the Save button on the Data Source editor page.
        """
        self.addDataPoints()
        
        if REQUEST and self.datapoints():

            datapoint = self.datapoints()[0]

            if REQUEST.has_key('rrdtype'):
                if REQUEST['rrdtype'] in datapoint.rrdtypes:
                    datapoint.rrdtype = REQUEST['rrdtype']
                else:
                    REQUEST['message'] = "%s is an invalid Type" % rrdtype
                    return self.callZenScreen(REQUEST)
            
            if REQUEST.has_key('rrdmin'):
                value = REQUEST['rrdmin']
                if value != '': 
                    try:
                        value = long(value)
                    except ValueError:
                        msg = "%s is an invalid RRD Min"
                        REQUEST['message'] = msg % value
                        return self.callZenScreen(REQUEST)
                datapoint.rrdmin = value
            
            if REQUEST.has_key('rrdmax'):
                value = REQUEST['rrdmax']
                if value != '': 
                    try:
                        value = long(value)
                    except ValueError:
                        msg = "%s is an invalid RRD Max"
                        REQUEST['message'] = msg % value
                        return self.callZenScreen(REQUEST)
                datapoint.rrdmax = value
            
            if REQUEST.has_key('createCmd'):
                datapoint.createCmd = REQUEST['createCmd']
        
        return RRDDataSource.zmanage_editProperties(self, REQUEST)


    def manage_addDataPointsToGraphs(self, ids=(), graphIds=(), REQUEST=None):
        """
        Override method in super class.  ids will always be an empty tuple, so
        call the super class's method with the single datapoint as the ids.
        """
        return RRDDataSource.manage_addDataPointsToGraphs(self, 
                (self.datapoints()[0].id,), graphIds, REQUEST)

