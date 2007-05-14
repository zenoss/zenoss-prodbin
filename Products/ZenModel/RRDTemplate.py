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

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Acquisition import aq_parent

from ZenModelRM import ZenModelRM

from Products.ZenRelations.RelSchema import *
import Products.ZenModel.RRDDataSource as RRDDataSource
from Products.ZenModel.BasicDataSource import BasicDataSource
from Products.ZenModel.ConfigurationError import ConfigurationError
from RRDDataPoint import SEPARATOR
from ZenPackable import ZenPackable


def manage_addRRDTemplate(context, id, REQUEST = None):
    """make a RRDTemplate"""
    tt = RRDTemplate(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDTemplate = DTMLFile('dtml/addRRDTemplate',globals())


def crumbspath(templ, crumbs, idx=-1):
    """Create the crumbs path for sub objects of an RRDTemplate.
    """
    dc = templ.deviceClass() 
    pt = "/perfConfig"
    if not dc: 
       dc = templ.getPrimaryParent()
       pt = "/objRRDTemplate"
    url = dc.getPrimaryUrlPath()+pt
    if pt == "/objRRDTemplate": 
        del crumbs[-2]
        idx = -1
    crumbs.insert(idx,(url,'PerfConf'))
    return crumbs



class RRDTemplate(ZenModelRM, ZenPackable):

    meta_type = 'RRDTemplate'

    security = ClassSecurityInfo()
  
    description = ""

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
        )

    _relations =  ZenPackable._relations + (
        ("deviceClass", ToOne(ToManyCont,"Products.ZenModel.DeviceClass", "rrdTemplates")),
        ("datasources", ToManyCont(ToOne,"Products.ZenModel.RRDDataSource", "rrdTemplate")),
        ("graphs", ToManyCont(ToOne,"Products.ZenModel.RRDGraph", "rrdTemplate")),
        ("thresholds", ToManyCont(ToOne,"Products.ZenModel.RRDThreshold", "rrdTemplate")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'viewRRDTemplate',
        'actions'        :
        ( 
            { 'id'            : 'overview'
            , 'name'          : 'Performance Template'
            , 'action'        : 'viewRRDTemplate'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(RRDTemplate, self).breadCrumbs(terminator)
        return crumbspath(self, crumbs)


    def isEditable(self, context):
        """Is this template editable in context.
        """
        return (self.isManager() and 
                (context == self or context.isLocalName(self.id)))

    
    def getGraphs(self):
        """Return our graphs objects in proper order.
        """
        graphs = self.graphs()
        graphs.sort(lambda x, y: cmp(x.sequence, y.sequence))
        return graphs 


    def getRRDPath(self):
        """Return the path on which this template is defined.
        """
        return self.getPrimaryParent().getPrimaryDmdId(subrel="rrdTemplates")
   

    def getRRDDataPointNames(self):
        """Return the list of all datapoint names.
        """
        return [p.name() for s in self.datasources() for p in s.datapoints()]

    
    def getRRDDataSources(self, type=None):
        """Return a list of all datapoints on this template.
        """
        if type is None: return self.datasources()
        return [ds for ds in self.datasources() if ds.sourcetype == type]


    def getRRDDataPoints(self):
        """Return a list of all datapoints on this template.
        """
        result = []
        for s in self.datasources():
            result.extend(s.datapoints())
        return result


    def getRRDDataPoint(self, name):
        """Return a datapoint based on its name.
        """
        source = name
        point = name
        if name.find(SEPARATOR) >= 0:
            source, point = name.split(SEPARATOR, 1)
        ds = self.datasources._getOb(source, None)
        if ds is None:
            results = []
            for ds in self.datasources():
                for dp in ds.datapoints():
                    if dp.name() == name:
                        results.append(dp)
            if len(results) == 1:
                return results[0]
        else:
            return ds.datapoints._getOb(point)
        raise ConfigurationError('Unknown data point "%s"' % name)


    security.declareProtected('Add DMD Objects', 'manage_addRRDDataSource')
    def manage_addRRDDataSource(self, id, dsOption, REQUEST=None):
        """Add an RRDDataSource to this DeviceClass.
        """
        ds = None
        if id and dsOption:
            ds = self.getDataSourceInstance(id, dsOption)
            self.datasources._setObject(ds.id, ds)
        if REQUEST:
            if ds:
                REQUEST['message'] = "Data source %s added" % ds.id
                url = '%s/datasources/%s' % (self.getPrimaryUrlPath(), ds.id)
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return ds


    security.declareProtected('Add Method Parameter', 'manage_addMethodParameter')
    def manage_addMethodParameter(self, newId, paramValue, paramType, REQUEST=None):
        """Add a method parameter.
        """
        if not paramValue: return
        ds = self.datasources._getOb(newId)
        try:
            #from RRDDataSource import convertMethodParameter
            convertMethodParameter(paramValue, paramType)
        except ValueError:
            REQUEST['message'] = "ERROR: %s could not be stored as type: %s" % (paramValue, paramType)
            return ds.callZenScreen(REQUEST)
        parameters = ds.xmlrpcMethodParameters
        parameters.append([paramValue, paramType])
        ds._setPropValue('xmlrpcMethodParameters', parameters)
        ds = self.datasources._getOb(newId)
        # save all the attributes on the page when the user clicks the add
        # parameter button so that other changes they have made are saved
        return ds.zmanage_editProperties(REQUEST)


    security.declareProtected('Delete Method Parameter', 'manage_deleteMethodParameter')
    def manage_deleteMethodParameter(self, newId, REQUEST=None):
        """Delete the last method parameter.
        """
        ds = self.datasources._getOb(newId)
        parameters = ds.xmlrpcMethodParameters
        parameters.pop()
        ds._setPropValue('xmlrpcMethodParameters', parameters)
        return ds.zmanage_editProperties(REQUEST)


    def callZenScreen(self, REQUEST, redirect=False):
        """Redirect to primary parent object if this template is locally defined
        """
        if REQUEST.get('zenScreenName',"") == "objRRDTemplate":
            return self.getPrimaryParent().callZenScreen(REQUEST, redirect)
        return super(RRDTemplate, self).callZenScreen(REQUEST, redirect)


    def manage_deleteRRDDataSources(self, ids=(), REQUEST=None):
        """Delete RRDDataSources from this DeviceClass 
        """
        def clean(rel, id):
            for obj in rel():
                if id in obj.dsnames:
                    obj.dsnames.remove(id)
                    if not obj.dsnames:
                        rel._delObject(obj.id)
            
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            self._p_changed = True
            if getattr(self.datasources,id,False):
                if getattr(self, 'device', False):
                    perfConf = self.device().getPerformanceServer()
                    perfConf.deleteRRDFiles(device=self.device().id, datasource=id)
                else:
                    for d in self.deviceClass.obj.getSubDevicesGen():
                        perfConf = d.getPerformanceServer()
                        perfConf.deleteRRDFiles(device=d, datasource=id)
                        
                self.datasources._delObject(id)
                clean(self.graphs, id)
                clean(self.thresholds, id)

        if REQUEST:
            if len(ids) == 1:
                REQUEST['message'] = 'Data source %s deleted.' % ids[0]
            elif len(ids) > 1:
                REQUEST['message'] = 'Data sources %s deleted.' % ', '.join(ids)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Add DMD Objects', 'manage_addRRDThreshold')
    def manage_addRRDThreshold(self, id, REQUEST=None):
        """Add an RRDThreshold to this DeviceClass.
        """
        from RRDThreshold import RRDThreshold
        if not id: return self.callZenScreen(REQUEST)
        org = RRDThreshold(id)
        self.thresholds._setObject(org.id, org)
        if REQUEST:
            if org:
                REQUEST['message'] = 'Threshold %s added' % org.id
                url = '%s/thresholds/%s' % (self.getPrimaryUrlPath(), org.id)
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return org
            

    def manage_deleteRRDThresholds(self, ids=(), REQUEST=None):
        """Delete RRDThresholds from this DeviceClass 
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            if getattr(self.thresholds,id,False):
                self.thresholds._delObject(id)
        if REQUEST:
            if len(ids) == 1:
                REQUEST['message'] = 'Threshold %s deleted.' % ids[0]
            elif len(ids) > 1:
                REQUEST['message'] = 'Thresholds %s deleted.' % ', '.join(ids)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_addRRDGraph')
    def manage_addRRDGraph(self, id="", REQUEST=None):
        """Add an RRDGraph to our RRDTemplate.
        """
        from RRDGraph import RRDGraph
        nextseq = 0
        graphs = self.getGraphs()
        if len(graphs) > 0:
            nextseq = graphs[-1].sequence + 1
        graph = None
        if id:
            graph = RRDGraph(id)
            graph.sequence = nextseq
            self.graphs._setObject(graph.id, graph)
        if REQUEST:
            if graph:
                REQUEST['message'] = 'Graph %s added' % graph.id
                url = '%s/graphs/%s' % (self.getPrimaryUrlPath(), graph.id)
                REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return graph
        

    security.declareProtected('Manage DMD', 'manage_deleteRRDGraphs')
    def manage_deleteRRDGraphs(self, ids=(), REQUEST=None):
        """Remove an RRDGraph from this RRDTemplate.
        """
        for id in ids:
            self.graphs._delObject(id)
            self.manage_resequenceRRDGraphs()
        if REQUEST:
            if len(ids) == 1:
                REQUEST['message'] = 'Graph %s deleted.' % ids[0]
            elif len(ids) > 1:
                REQUEST['message'] = 'Graphs %s deleted.' % ', '.join(ids)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_resequenceRRDGraphs')
    def manage_resequenceRRDGraphs(self, seqmap=(), origseq=(), REQUEST=None):
        """Reorder the sequecne of the RRDGraphs.
        """
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.getGraphs(), seqmap, origseq, REQUEST)


    def getDataSourceClasses(self):
        dsClasses = [BasicDataSource]
        for zp in self.dmd.packs():
            dsClasses += zp.getDataSourceClasses()
        return dsClasses
        
        
    def getDataSourceOptions(self):
        ''' Returns a list of the available datasource options as a list
        of (display name, dsOption)
        '''
        dsTypes = []
        for dsClass in self.getDataSourceClasses():
            dsTypes += [(t, '%s.%s' % (dsClass.__name__, t)) 
                            for t in dsClass.sourcetypes]
        return dsTypes
        

    def getDataSourceInstance(self, id, dsOption):
        ''' Given one of the dsOptions returned by getDataSourceOptions)
        return an instance of the that RRDDataSource subclass.
        '''
        dsClassName, dsType = dsOption.split('.')
        for c in self.getDataSourceClasses():
            if dsClassName == c.__name__:
                ds = c(id)
                ds.sourcetype = dsType
                break
        else:
            raise ConfigurationError('Cannot find datasource class'
                        ' for %s' % dsOption)
        return ds

InitializeClass(RRDTemplate)
