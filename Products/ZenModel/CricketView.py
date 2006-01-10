#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""CricketView

$Id: CricketView.py,v 1.13 2004/04/06 21:05:03 edahl Exp $"""

__version__ = "$Revision: 1.13 $"[11:-2]

import types

from Acquisition import aq_base


class CricketView:
    """
    Mixin to provide hooks to cricket management functions
    which allow targetmap management and graphing
    configuration generation is in CricketDevice and CricketServer
    """

    def cricketGraphUrl(self, target=None, targettype=None, 
                        view=None, drange=None):
        """resolve targettype and view names to objects 
        and pass to cricketconf"""
        from Products.ZenRRD.utils import getRRDView
        if not drange: drange = self.defaultDateRange
        if target: targettype = self.getCricketTypeForTarget(target)
        if not target: target = self.id
        if not targettype: targettype = self.getCricketTargetType()
        targetpath = self.cricketTargetPath() + '/' + target.lower()
        if targetpath[-4:] != '.rrd': targetpath+='.rrd'
        objpaq = self.primaryAq()
        targettype = self.getCricketTarget(targettype)
        if not view:
            view = targettype.getDefaultView(objpaq)
        else:
            view = getRRDView(objpaq, view)
        cricketserver = objpaq.getCricketServer()
        if cricketserver:
            return cricketserver.cricketGraphUrl(objpaq, targetpath, 
                                             targettype, view, drange)
        

    def cricketMGraphUrl(self, targetsmap, view=None, drange=None):
        """resolve targetsmap and view and send to cricketconf"""
        from Products.ZenRRD.utils import getRRDView
        if not drange: drange = self.defaultDateRange
        objpaq = self.primaryAq()
        view = getRRDView(objpaq, view)
        cricketserver = objpaq.getCricketServer()
        ntm = []
        for target, targettype in targetsmap:
            targettype = self.getCricketTarget(targettype)
            ntm.append((target, targettype))
        if cricketserver:
            return cricketserver.cricketMGraphUrl(objpaq, ntm, view, drange)
                                                
         
    def setCricketTargetMap(self, targetpath, targets):
        """build the cricket target map for an object
        used when we want to draw graphs for the object"""
        tm = {}
        if type(targets) != types.ListType and type(targets) != types.TupleType:
            targets = (targets,)
        for targetdata in targets:
            name = targetdata['target']
            if name == '--default--': continue
            ttype = targetdata['target-type']
            tm[name] = ttype
        if tm != self._cricketTargetMap:
            self._cricketTargetMap = tm
            self._p_changed = 1
        if self._cricketTargetPath != targetpath:
            self._cricketTargetPath = targetpath
        

    def cricketTargetPath(self):
        """Return the cricket target path set for this object.
        """
        return self._cricketTargetPath
    

    def clearCricketMGraph(self):
        self._mgraphs = []


    def addCricketMGraph(self, mgraph):
        """add a RRDMGraph to the mgraph list for this object"""
        self._mgraphs.append(mgraph)


    def getCricketMGraphs(self):
        """returns a list of RRDMGraphs"""
        return self._mgraphs


    def checkCricketData(self):
        """check to see if there is cricket data for this object"""
        return self.getCricketTargetMap() or self.getCricketMGraphs()


    def getDefaultGraphs(self, drange=None):
        """get the default graph list for this object"""
        targets = self.getCricketTargets()
        graphs = []
        if len(targets) == 1:
            targettype = self.getCricketTargetType()
            views = self.getCricketViewsForTarget(targettype)
            for view in views:
                graph = {}
                graph['title'] = view
                graph['url'] = self.cricketGraphUrl(view=view,drange=drange)
                if graph['url']:
                    graphs.append(graph)
        else:
            for target in targets:
                graph = {}
                graph['title'] = target
                graph['url'] = self.cricketGraphUrl(target=target,drange=drange)
                if graph['url']:
                    graphs.append(graph)
        for mgraph in self.getCricketMGraphs():
            for view in mgraph.getViews():
                graph = {}
                graph['title'] = view
                graph['url'] = self.cricketMGraphUrl(mgraph.getMTargets(), 
                                                    view, drange=drange)
                graphs.append(graph)
        return graphs
            
    
    def getCricketTargets(self):
        """return list of target names for a cricket object"""
        return self._cricketTargetMap.keys()


    def getCricketTargetMap(self):
        """return the entire targetmap"""
        if not hasattr(self, '_cricketTargetMap'):
            self._cricketTargetMap = {}
        return self._cricketTargetMap

    
    def getCricketTargetType(self):
        """return the target type of this instnace 
        if there is more than one will return but which is arbitrary"""
        if len(self._cricketTargetMap) > 0:
            return self._cricketTargetMap.values()[0]


    def getCricketTypeForTarget(self, target):
        """lookup the type of a target for this object we try
        both the full target passed as well as the last section
        when split by a '/'"""
        return self._cricketTargetMap.get(target, None)
    

    def getCricketTarget(self, targettypename):
        """lookup a targettype from its name"""
        from Products.ZenRRD.utils import getRRDTargetType
        return getRRDTargetType(self.primaryAq(), targettypename)


    def getCricketViewsForTarget(self, targettypename):
        """get the views for a particular targetname"""
        target = self.getCricketTarget(targettypename)
        return target.getViewNames()


    def lookupCricketInterfaceGraphs(self, id):
        """lookup cricket"""
        if hasattr(self, 'interfaces'):
            intrel = self.interfaces
            for att in intrel.objectIds():
                if att.lower() == id:
                    obj = intrel._getOb(att)
                    #return obj.viewPerformanceDetail(self.REQUEST)
                    return obj.viewPerformanceDetail()
