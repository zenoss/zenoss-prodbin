#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

import types

from Acquisition import aq_base


class RRDView:
    """
    Mixin to provide hooks to RRD management functions
    which allow targetmap management and graphing
    configuration generation is in CricketDevice and CricketServer
    """

    def rrdGraphUrl(self, targettype=None, view=None, drange=None):
        """resolve targettype and view names to objects 
        and pass to view performance"""
        from Products.ZenRRD.utils import getRRDView
        if not drange: drange = self.defaultDateRange
        if not targettype: targettype = self.getRRDTargetType()
        targetpath = self.getPrimaryDmdId()
        objpaq = self.primaryAq()
        if not view:
            view = targettype.getDefaultView(objpaq)
        else:
            view = getRRDView(objpaq, view)
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
            
    
    def getRRDTargetName(self):
        """Return the target type name of this component.  By default meta_type.
        Override to create custom type selection.
        """
        return self.meta_type


    def getRRDTargetType(self):
        """lookup a targettype from its name"""
        from Products.ZenRRD.utils import getRRDTargetType
        return getRRDTargetType(self.primaryAq(), self.getRRDTargetName())


    def getRRDViews(self):
        """get the views for a particular targetname"""
        target = self.getRRDTargetType()
        return target.getViewNames()
