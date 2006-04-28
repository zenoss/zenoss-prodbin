#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import os
import types

from Acquisition import aq_base, aq_chain

from Products.ZenRRD.Exceptions import RRDObjectNotFound 


class RRDView(object):
    """
    Mixin to provide hooks to RRD management functions
    which allow targetmap management and graphing
    configuration generation is in CricketDevice and CricketServer
    """

    def getRRDGraphUrl(self, graph, drange=None, template=None):
        """resolve template and graph names to objects 
        and pass to graph performance"""
        if not drange: drange = self.defaultDateRange
        if not template: template = self.getRRDTemplate()
        if type(graph) in types.StringTypes: 
            graph = template.graphs._getOb(graph)
        targetpath = self.getPrimaryDmdId()
        objpaq = self.primaryAq()
        perfServer = objpaq.getPerformanceServer()
        if perfServer:
            return perfServer.performanceGraphUrl(objpaq, targetpath, 
                                                  template, graph, drange)
        

    def getRRDValue(self, dsname, drange=None, function="LAST"):
        """Return a single rrd value from its file using function.
        """
        dsnames = (dsname,)
        return self.getRRDValues(dsnames, drange, function)[dsname]

        
    def getRRDValues(self, dsnames, drange=None, function="LAST"):
        """Return a dict of key value pairs where dsnames are the keys.
        """
        if not drange: drange = self.defaultDateRange
        #template = Set(self.getRRDTemplate())
        #if dsnames not in template: raise
        gopts = []
        basepath = self.getPrimaryDmdId()
        for dsname in dsnames:
            filename = os.path.join(basepath, dsname) + ".rrd"
            gopts.append("DEF:%s_r=%s:ds0:AVERAGE" % (dsname,filename))
            gopts.append("VDEF:%s=%s_r,%s" % (dsname,dsname,function))
            gopts.append("PRINT:%s:%%.2lf" % (dsname))
        perfServer = self.getPerformanceServer()
        if perfServer:
            vals = perfServer.performanceCustomSummary(gopts, drange)
        res = {}
        for key,val in zip(dsnames, vals): res[key] = float(val)
        return res
        
        
    
    def getDefaultGraphs(self, drange=None):
        """get the default graph list for this object"""
        graphs = []
        template = self.getRRDTemplate()
        if not template: return graphs
        for g in template.getGraphs():
            graph = {}
            graph['title'] = g.getId()
            graph['url'] = self.getRRDGraphUrl(g,drange,template=template)
            if graph['url']:
                graphs.append(graph)
        return graphs
            
    
    def getRRDTemplateName(self):
        """Return the target type name of this component.  By default meta_type.
        Override to create custom type selection.
        """
        return self.meta_type


    def snmpIgnore(self):
        """Should this component be monitored for performance using snmp.
        """
        return False


    def getRRDTemplate(self, name=None):
        """Return the closest RRDTemplate named name by walking our aq chain.
        """
        if not name: name = self.getRRDTemplateName()
        mychain = aq_chain(self)
        for obj in mychain:
            if not getattr(aq_base(obj), 'rrdTemplates', False): continue
            if getattr(aq_base(obj.rrdTemplates), name, False):
                return obj.rrdTemplates._getOb(name)


    def getThresholds(self, templ):
        """Return a dictionary where keys are dsnames and values are thresholds.
        """
        map = {}
        for thresh in templ.thresholds():
            for dsname in thresh.dsnames:
                threshdef = map.setdefault(dsname, [])
                threshdef.append(thresh.getConfig(self))
        return map

        
    def getSnmpOidTargets(self):
        """Return a list of (name, oid, path, type, createCmd, thresholds)
        that define monitorable"""
        oids = []
        if self.snmpIgnore(): return oids 
        basepath = self.getPrimaryDmdId()
        try:
            templ = self.getRRDTemplate(self.getRRDTemplateName())
            if templ:
                threshs = self.getThresholds(templ)
                for ds in templ.getRRDDataSources():
                    oid = ds.oid
                    snmpindex = getattr(self, "ifindex", self.snmpindex)
                    if snmpindex: oid = "%s.%s" % (oid, snmpindex)
                    cname = self.meta_type != "Device" \
                                and self.viewName() or ds.id
                    oids.append((cname,
                                 oid,
                                 "/".join((basepath, ds.id)),
                                 ds.rrdtype,
                                 ds.createCmd,
                                 threshs.get(ds.id,[])))
        except RRDObjectNotFound, e:
            log.warn(e)
        return oids


    def copyRRDTemplate(self, REQUEST=None):
        """Make a local copy of our RRDTemplate if one doesn't exist.
        """
        templ = self.getRRDTemplate()
        if not self.isLocalName(templ.id):
            ct = templ._getCopy(self)
            self._setObject(ct.id, ct)
        if REQUEST: return self.callZenScreen(REQUEST)


    def deleteRRDTemplate(self, REQUEST=None):
        """Delete our local RRDTemplate if it exists.
        """
        tname = self.getRRDTemplateName()
        if self.isLocalName(tname):
            self._delObject(tname)
        if REQUEST: return self.callZenScreen(REQUEST)
