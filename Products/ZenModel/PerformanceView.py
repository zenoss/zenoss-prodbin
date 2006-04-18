#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""CricketView

$Id: CricketView.py,v 1.13 2004/04/06 21:05:03 edahl Exp $"""

__version__ = "$Revision: 1.13 $"[11:-2]

import types

from Acquisition import aq_base


class PerformanceView:
    """
    Mixin to provide hooks to performance management functions
    which allow targetmap management and graphing
    configuration generation is in PerformanceDevice and PerformanceServer
    """

    def performanceGraphUrl(self, target=None, targettype=None, 
                        view=None, drange=None):
        """resolve targettype and view names to objects 
        and pass to performanceconf"""
        from Products.ZenRRD.utils import getRRDView
        if not drange: drange = self.defaultDateRange
        if target: targettype = self.getPerformanceTypeForTarget(target)
        if not target: target = self.id
        if not targettype: targettype = self.getPerformanceTargetType()
        targetpath = self.performanceTargetPath() + '/' + target.lower()
        if targetpath[-4:] != '.rrd': targetpath+='.rrd'
        objpaq = self.primaryAq()
        targettype = self.getPerformanceTarget(targettype)
        if not view:
            view = targettype.getDefaultView(objpaq)
        else:
            view = getRRDView(objpaq, view)
        performanceserver = objpaq.getPerformanceServer()
        if performanceserver:
            return performanceserver.performanceGraphUrl(objpaq, targetpath, 
                                             targettype, view, drange)
        

    def performanceMGraphUrl(self, targetsmap, view=None, drange=None):
        """resolve targetsmap and view and send to perfconf"""
        from Products.ZenRRD.utils import getRRDView
        if not drange: drange = self.defaultDateRange
        objpaq = self.primaryAq()
        view = getRRDView(objpaq, view)
        performanceserver = objpaq.getPerformanceServer()
        ntm = []
        for target, targettype in targetsmap:
            targettype = self.getPerformanceTarget(targettype)
            ntm.append((target, targettype))
        if performanceserver:
            return performanceserver.performanceMGraphUrl(objpaq, ntm, view, drange)
                                                
         
    def setPerformanceTargetMap(self, targetpath, targets):
        """build the performance target map for an object
        used when we want to draw graphs for the object"""
        tm = {}
        if type(targets) != types.ListType and type(targets) != types.TupleType:
            targets = (targets,)
        for targetdata in targets:
            name = targetdata['target']
            if name == '--default--': continue
            ttype = targetdata['target-type']
            tm[name] = ttype
        if tm != self._performanceTargetMap:
            self._performanceTargetMap = tm
            self._p_changed = 1
        if self._performanceTargetPath != targetpath:
            self._performanceTargetPath = targetpath
        

    def performanceTargetPath(self):
        """Return the performance target path set for this object.
        """
        return self._performanceTargetPath
    

    def clearPerformanceMGraph(self):
        self._mgraphs = []


    def addPerformanceMGraph(self, mgraph):
        """add a RRDMGraph to the mgraph list for this object"""
        self._mgraphs.append(mgraph)


    def getPerformanceMGraphs(self):
        """returns a list of RRDMGraphs"""
        return self._mgraphs


    def checkPerformanceData(self):
        """check to see if there is performance data for this object"""
        return self.getPerformanceTargetMap() or self.getPerformanceMGraphs()


    def getDefaultGraphs(self, drange=None):
        """get the default graph list for this object"""
        targets = self.getPerformanceTargets()
        graphs = []
        if len(targets) == 1:
            targettype = self.getPerformanceTargetType()
            views = self.getPerformanceViewsForTarget(targettype)
            for view in views:
                graph = {}
                graph['title'] = view
                graph['url'] = self.performanceGraphUrl(view=view,drange=drange)
                if graph['url']:
                    graphs.append(graph)
        else:
            for target in targets:
                graph = {}
                graph['title'] = target
                graph['url'] = self.performanceGraphUrl(target=target,drange=drange)
                if graph['url']:
                    graphs.append(graph)
        for mgraph in self.getPerformanceMGraphs():
            for view in mgraph.getViews():
                graph = {}
                graph['title'] = view
                graph['url'] = self.performanceMGraphUrl(mgraph.getMTargets(), 
                                                    view, drange=drange)
                graphs.append(graph)
        return graphs
            
    
    def getPerformanceTargets(self):
        """return list of target names for a performance object"""
        return self._performanceTargetMap.keys()


    def getPerformanceTargetMap(self):
        """return the entire targetmap"""
        if not hasattr(self, '_performanceTargetMap'):
            self._performanceTargetMap = {}
        return self._performanceTargetMap

    
    def getPerformanceTargetType(self):
        """return the target type of this instnace 
        if there is more than one will return but which is arbitrary"""
        if len(self._performanceTargetMap) > 0:
            return self._performanceTargetMap.values()[0]


    def getPerformanceTypeForTarget(self, target):
        """lookup the type of a target for this object we try
        both the full target passed as well as the last section
        when split by a '/'"""
        return self._performanceTargetMap.get(target, None)
    

    def getPerformanceTarget(self, targettypename):
        """lookup a targettype from its name"""
        from Products.ZenRRD.utils import getRRDTargetType
        return getRRDTargetType(self.primaryAq(), targettypename)


    def getPerformanceViewsForTarget(self, targettypename):
        """get the views for a particular targetname"""
        target = self.getPerformanceTarget(targettypename)
        return target.getViewNames()


    def lookupPerformanceInterfaceGraphs(self, id):
        """lookup performance"""
        if hasattr(self, 'interfaces'):
            intrel = self.interfaces
            for att in intrel.objectIds():
                if att.lower() == id:
                    obj = intrel._getOb(att)
                    #return obj.viewPerformanceDetail(self.REQUEST)
                    return obj.viewPerformanceDetail()
