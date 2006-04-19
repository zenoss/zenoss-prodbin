#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""RRDGraph

RRDGraph defines the global options for an rrdtool graph.
"""

import time

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions

from Products.ZenRelations.RelSchema import *

from ZenModelRM import ZenModelRM


def manage_addRRDGraph(context, id, REQUEST = None):
    """make a RRDGraph"""
    graph = RRDGraph(id)
    context._setObject(graph.id, graph)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDGraph = DTMLFile('dtml/addRRDGraph',globals())


class RRDGraph(ZenModelRM):

    meta_type = 'RRDGraph'
   
    security = ClassSecurityInfo()

    dsnames = []
    height = 100
    width = 400
    threshmap = []
    units = ""
    log = False
    linewidth = 1
    base = False
    stacked = False
    summary = True
    miny = -1
    maxy = -1


    _properties = (
        {'id':'dsnames', 'type':'lines', 'mode':'w'},
        {'id':'height', 'type':'int', 'mode':'w'},
        {'id':'width', 'type':'int', 'mode':'w'},
        {'id':'units', 'type':'string', 'mode':'w'},
        {'id':'linewidth', 'type':'int', 'mode':'w'},
        {'id':'log', 'type':'boolean', 'mode':'w'},
        {'id':'base', 'type':'boolean', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        {'id':'summary', 'type':'boolean', 'mode':'w'},
        {'id':'miny', 'type':'int', 'mode':'w'},
        {'id':'maxy', 'type':'int', 'mode':'w'},
        {'id':'colors', 'type':'lines', 'mode':'w'},
        )

    _relations =  (
        ("rrdTemplate", ToOne(ToManyCont,"RRDTemplate", "graphs")),
        )

    colors = (
        '#00cc00', '#0000ff', '#00ffff', '#ff0000', 
        '#ffff00', '#cc0000', '#0000cc', '#0080c0',
        '#8080c0', '#ff0080', '#800080', '#0000a0',
        '#408080', '#808000', '#000000', '#00ff00',
        '#fb31fb', '#0080ff', '#ff8000', '#800000', 
        )

    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'viewRRDGraph',
        'actions'        :
        ( 
            { 'id'            : 'overview'
            , 'name'          : 'Overview'
            , 'action'        : 'viewRRDGraph'
            , 'permissions'   : ( Permissions.view, )
            },
            { 'id'            : 'edit'
            , 'name'          : 'Edit'
            , 'action'        : 'editRRDGraph'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )
    
    def graphOpts(self, context, rrdfile, targettype):
        """build the graph opts for a single rrdfile"""
        self._v_dsindex = 0
        self._v_threshcoloridx = len(self.colors)
        gopts = self._graphsetup()
        gopts = self._buildds(gopts, context, rrdfile, targettype, self.summary)
        gopts = self._thresholds(gopts, context, targettype)
        return gopts

    
    def summaryOpts(self, context, rrdfile, targettype):
        """build just the summary of graph data with no graph"""
        gopts = []
        self._v_dsindex = 0
        self._buildds(gopts, context, rrdfile, targettype, self.summary)
        return gopts


    def _graphsetup(self):
        gopts = []
        if self.height:
            gopts.append('--height=%d' % self.height)
        if self.width:
            gopts.append('--width=%d' % self.width)
        if self.log:
            gopts.append('--logarithmic')
        if self.maxy > -1:
            gopts.append('--upper-limit=%d' % self.maxy)
        if self.miny > -1:
            gopts.append('--lower-limit=%d' % self.miny)
        if self.units: 
            gopts.append('--vertical-label=%s' % self.units)
            if self.units == 'percentage':
                if not self.maxy > -1:
                    gopts.append('--upper-limit=100')
                if not self.miny > -1:
                    gopts.append('--lower-limit=0')
                gopts.append('--rigid')
        if self.base:
            gopts.append('--base=1024')
        return gopts
       

    def _buildds(self, gopts, context, rrdfile, targettype, summary, multiid=-1): 
        for dsname in self.dsnames:
            ds = self.getRRDDataSource(dsname) #aq
            gopts += ds.graphOpts(rrdfile, self._getcolor(),
                                self._gettype(), summary, multiid)
            self._v_dsindex += 1


    def _thresholds(self, context, targettype):
        """build the hrule opts for any thresholds that apply to our graph"""
        allthreshs = targettype.getThresholds(context) 
        threshs = []
        for thresh in allthreshs:
            for dsname in thresh.dsnames:
                if dsname in self.dsnames:
                    threshs.append(thresh)
                    break
        if threshs: gopts.append("COMMENT:Data Thresholds\j")
        for thresh in threshs:
            if thresh.meta_type == 'RRDThreshold':
                minvalue = thresh.getGraphMinval(context)
                if minvalue and minvalue != 'n':
                    minvalue = str(minvalue)
                    minvalue += self._getthreshcolor()
                    gopts.append("HRULE:%s:%s" % 
                            (minvalue, thresh.getMinLabel(context)))
                maxvalue = thresh.getGraphMaxval(context)
                if maxvalue:
                    maxvalue = str(maxvalue)
                    maxvalue += self._getthreshcolor()
                    gopts.append("HRULE:%s:%s" % 
                            (maxvalue, thresh.getMaxLabel(context)))


    def _getthreshcolor(self):
        """get a threshold color by working backwards down the color list"""
        self._v_threshcoloridx -= 1
        a= self.colors[self._v_threshcoloridx]
        return a


    def _getcolor(self):
        """get a default datasource color by working forwards on the ds list"""
        return self.colors[self._v_dsindex]


    def _gettype(self):
        """get a default graph type first is area rest are lines"""
        if self._v_dsindex == 0:
            return "AREA"
        elif self.stacked:
            return "STACK"
        else:
            return "LINE%d" % self.linewidth

InitializeClass(RRDGraph)
