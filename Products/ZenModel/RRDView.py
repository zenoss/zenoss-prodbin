#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import types

from Acquisition import aq_base, aq_chain

from Products.ZenRRD.Exceptions import RRDObjectNotFound 


class RRDView(object):
    """
    Mixin to provide hooks to RRD management functions
    which allow targetmap management and graphing
    configuration generation is in CricketDevice and CricketServer
    """

    def rrdGraphUrl(self, targettype, view, drange):
        """resolve targettype and view names to objects 
        and pass to view performance"""
        if not drange: drange = self.defaultDateRange
        # if not targettype: targettype = self.getRRDTemplate()
        targetpath = self.getPrimaryDmdId()
        objpaq = self.primaryAq()
        # view = targettype.getDefaultView(objpaq)
        perfServer = objpaq.getPerformanceServer()
        if perfServer:
            return perfServer.performanceGraphUrl(objpaq, targetpath, 
                                                  targettype, view, drange)
        

    def getDefaultGraphs(self, drange=None):
        """get the default graph list for this object"""
        graphs = []
        template = self.getRRDTemplate(self.getRRDTemplateName())
        if not template: return graphs
        for g in template.getGraphs():
            graph = {}
            graph['title'] = g.getId()
            graph['url'] = self.rrdGraphUrl(template,g,drange)
            if graph['url']:
                graphs.append(graph)
        return graphs
            
    
    def getRRDTemplateName(self):
        """Return the target type name of this component.  By default meta_type.
        Override to create custom type selection.
        """
        return self.meta_type


    if 0: # def getRRDTemplate(self):
        """lookup a Template from its name"""
        from Products.ZenRRD.utils import getRRDTemplate
        return getRRDTemplate(self.primaryAq(), self.getRRDTemplateName())


    if 0: # def getRRDViews(self):
        """get the views for a particular targetname"""
        target = self.getRRDTemplate(self.getRRDTemplateName())
        return target.getViewNames()


    def snmpIgnore(self):
        """Should this component be monitored for performance using snmp.
        """
        return False


    def getRRDTemplate(self, name):
        """Return the closest RRDTemplate named name by walking our aq chain.
        """
        mychain = aq_chain(self)
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
            if ttype:
                for ds in ttype.getRRDDataSources():
                    oid = ds.oid
                    snmpindex = getattr(self, "ifindex", self.snmpindex)
                    if snmpindex: oid = "%s.%s" % (oid, snmpindex)
                    oids.append((oid,
                                 "/".join((basepath, ds.id)),
                                 ds.rrdtype))
        except RRDObjectNotFound, e:
            log.warn(e)
        return oids
