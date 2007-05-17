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

from Globals import DTMLFile
from Globals import InitializeClass
from DateTime import DateTime
from Acquisition import aq_parent
from AccessControl import ClassSecurityInfo, Permissions

from Products.PageTemplates.Expressions import getEngine

from Products.ZenUtils.ZenTales import talesCompile
from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable


#def manage_addRRDDataSource(context, id, dsClassName, dsType, REQUEST = None):
#    """make a RRDDataSource"""
#    raise '####### HEY #####'
#    for dsClass in 
#    ds = RRDDataSource(id)
#    context._setObject(ds.id, ds)
#    if REQUEST is not None:
#        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

#addRRDDataSource = DTMLFile('dtml/addRRDDataSource',globals())


def convertMethodParameter(value, type):
    if type == "integer":
        return int(value)
    elif type == "string":
        return str(value)
    elif type == "float":
        return float(value)
    else:
        raise TypeError('Unsupported method parameter type: %s' % type)



#class RRDDataSourceError(Exception): pass


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
                        perfConf.deleteRRDFiles(device=d, datapoint=dp.name())
        
                clean(self.graphs, dp.name())
                clean(self.thresholds, dp.name())
                self.datapoints._delObject(dp.id)
                
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    def getCommand(self, context, cmd=None):
        """Return localized command target.
        """
        # Perform a TALES eval on the expression using self
        if cmd is None:
            cmd = self.commandTemplate
        exp = "string:"+ cmd
        compiled = talesCompile(exp)    
        d = context.device()
        environ = {'dev' : d,
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


    def checkCommandPrefix(self, context, cmd):
        if not cmd.startswith('/') and not cmd.startswith('$'):
            if not cmd.startswith(context.zCommandPath):
                cmd = os.path.join(context.zCommandPath, cmd)
        return cmd


    def getSeverityString(self):
        return self.ZenEventManager.getSeverityString(self.severity)


    def zmanage_editProperties(self, REQUEST=None):
        return ZenModelRM.zmanage_editProperties(self, REQUEST)
