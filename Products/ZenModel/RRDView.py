#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import types

from Acquisition import aq_base

from Products.ZenRRD.Exceptions import RRDObjectNotFound 


class RRDView(object):
    """
    Mixin to provide hooks to RRD management functions
    which allow targetmap management and graphing
    configuration generation is in CricketDevice and CricketServer
    """

    def rrdGraphUrl(self, targettype=None, view=None, drange=None):
        """resolve targettype and view names to objects 
        and pass to view performance"""
        if not drange: drange = self.defaultDateRange
        if not targettype: targettype = self.getRRDTargetType()
        targetpath = self.getPrimaryDmdId()
        objpaq = self.primaryAq()
        view = targettype.getDefaultView(objpaq)
        perfServer = objpaq.getPerformanceServer()
        if perfServer:
            return perfServer.performanceGraphUrl(objpaq, targetpath, 
                                                  targettype, view, drange)
        

    def getDefaultGraphs(self, drange=None):
        """get the default graph list for this object"""
        graphs = []
        views = self.getRRDViews()
        for view in views:
            graph = {}
            graph['title'] = view
            graph['url'] = self.rrdGraphUrl(view=view,drange=drange)
            if graph['url']:
                graphs.append(graph)
        return graphs
            
    
    def getRRDTemplateName(self):
        """Return the target type name of this component.  By default meta_type.
        Override to create custom type selection.
        """
        return self.meta_type


    def getRRDTemplate(self):
        """lookup a Template from its name"""
        from Products.ZenRRD.utils import getRRDTemplate
        return getRRDTemplate(self.primaryAq(), self.getRRDTemplateName())


    def getRRDViews(self):
        """get the views for a particular targetname"""
        target = self.getRRDTemplate()
        return target.getViewNames()


    def snmpIgnore(self):
        """Should this component be monitored for performance using snmp.
        """
        return False


    def getRRDTemplate(self, name):
        """Return the closest RRDTemplate named name by walking our aq chain.
        """
        mychain = aq_chain(self)
        mychain.reverse()
        for obj in mychain:
            if not getattr(aq_base(obj), 'rrdTemplates', False): continue
            if getattr(aq_base(obj.rrdTemplates), name, False):
                return obj.rrdTemplates._getOb(name)


    def getSnmpOidTargets(self):
        """Return a list of (oid, path, type) that define monitorable 
        """
        oids = []
        if self.snmpIgnore(): return oids 
        basepath = self.getPrimaryDmdId()
        try:
            ttype = self.getRRDTemplate(self.getRRDTemplateName())
            for dsname in ttype.dsnames:
                ds = ttype.getDs(self, dsname)
                oid = ds.oid
                snmpindex = getattr(self, "ifindex", self.snmpindex) #FIXME
                if ds.isrow: oid = "%s.%d" % (oid, snmpindex)
                oids.append((oid, "/".join((basepath, dsname)), ds.rrdtype))
        except RRDObjectNotFound, e:
            log.warn(e)
        return oids
