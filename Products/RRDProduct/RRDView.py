#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RRDView

RRDView defines the global options for an rrdtool graph.

$Id: RRDView.py,v 1.22 2003/11/22 16:26:00 edahl Exp $"""

__version__ = "$Revision: 1.22 $"[11:-2]

import time

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from OFS.PropertyManager import PropertyManager

import utils

from RRDToolItem import RRDToolItem

def manage_addRRDView(context, id, REQUEST = None):
    """make a RRDView"""
    view = RRDView(id)
    context._setObject(view.id, view)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDView = DTMLFile('dtml/addRRDView',globals())


class RRDViewError(Exception): pass

class RRDView(RRDToolItem, PropertyManager):

    meta_type = 'RRDView'
   
    security = ClassSecurityInfo()

    manage_options = PropertyManager.manage_options + \
                     RRDToolItem.manage_options
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

    colors = (
        '#00cc00', '#0000ff', '#00ffff', '#ff0000', 
        '#ffff00', '#cc0000', '#0000cc', '#0080c0',
        '#8080c0', '#ff0080', '#800080', '#0000a0',
        '#408080', '#808000', '#000000', '#00ff00',
        '#fb31fb', '#0080ff', '#ff8000', '#800000', 
        )

    def __init__(self, id, dsnames=[], height=100, width=400, 
                units='', log=0, linewidth=1, threshmap=[], 
                base=0, stacked=0, summary=1, maxy=-1, miny=-1): 
        self.id = utils.prefixid(self.meta_type, id)
        self._dsnames = dsnames
        self.height = height
        self.width = width
        self.threshmap = threshmap
        self.units = units
        self.log = log
        self.linewidth = int(linewidth)
        self.base = base
        self.stacked = stacked
        self.summary = summary
        self.miny = miny
        self.maxy = maxy
        self._v_gopts = []
        self._v_dsindex = 0
        self._v_threshcoloridx = len(self.colors)


    def textload(self, args):
        """called by RRDLoader to populate a RRDView"""
        utils.loadargs(self, args)


    def __getattr__(self, name):
        if name == 'dsnames':
            return self._dsnames
        #elif name == 'colors':
        #    return self._colors
        else:
            raise AttributeError, name


    def _setPropValue(self, id, value):
        """override from PerpertyManager to handle checks and ip creation"""
        self._wrapperCheck(value)
        if id == 'dsnames':
            self.setDsNames(value)
        #if id == 'colors':
        #    self.setColors(value)
        else:    
            setattr(self,id,value)

    
    def graphOpts(self, context, rrdfile, targettype):
        """build the graph opts for a single rrdfile"""
        self._v_gopts = []
        self._v_dsindex = 0
        self._v_threshcoloridx = len(self.colors)
        self._graphsetup()
        self._buildds(context, rrdfile, targettype, self.summary)
        self._thresholds(context, targettype)
        return self._v_gopts

    
    def summaryOpts(self, context, rrdfile, targettype):
        """build just the summary of view data with no graph"""
        self._v_gopts = []
        self._v_dsindex = 0
        self._buildds(context, rrdfile, targettype, self.summary)
        return self._v_gopts


    def multiGraphOpts(self, context, targetToTypeMap):
        """build the graph opts for multiple rrdfiles
        that may have different datasources and different types"""
        self._v_gopts = []
        self._v_dsindex = 0
        self._v_threshcoloridx = len(self.colors)
        self._graphsetup()
        i = 0
        for target, targettype in targetToTypeMap:
            self._buildds(context, target, targettype, self.summary, multiid=i)
            i += 1
        self._thresholds(context, targettype)
        return self._v_gopts



    def setDsNames(self, dsnames):
        """set the entire list of datasource names"""
        self._dsnames = []
        map(self.addDs, dsnames)


    def addDs(self, dsname):
        if dsname:
            self._dsnames.append(dsname)
            self._p_changed = 1 

    
    def setColors(self, colors):
        """set the entire list of datasource names"""
        self._colors = []
        map(self.addColor, colors)


    def addColor(self, color):
        if color:
            self._colors.append( color)
            self._p_changed = 1 

    
    def _graphsetup(self):
        if self.height:
            self._v_gopts.append('--height=%d' % self.height)
        if self.width:
            self._v_gopts.append('--width=%d' % self.width)
        if self.log:
            self._v_gopts.append('--logarithmic')
        if self.maxy > -1:
            self._v_gopts.append('--upper-limit=%d' % self.maxy)
        if self.miny > -1:
            self._v_gopts.append('--lower-limit=%d' % self.miny)
        if self.units: 
            self._v_gopts.append('--vertical-label=%s' % self.units)
            if self.units == 'percentage':
                if not self.maxy > -1:
                    self._v_gopts.append('--upper-limit=100')
                if not self.miny > -1:
                    self._v_gopts.append('--lower-limit=0')
                self._v_gopts.append('--rigid')
        if self.base:
            self._v_gopts.append('--base=1024')
       

    def _buildds(self, context, rrdfile, targettype, summary, multiid=-1): 
        from RRDTargetType import RRDTargetTypeError
        for dsname in self._dsnames:
            ds = None
            try:
                ds = targettype.getDs(context, dsname)
            except RRDTargetTypeError:
                # if the target doesn't have the data source skip it
                pass
            if ds:
                index = ds.getIndex()
                self._v_gopts += ds.graphOpts(rrdfile, self._getcolor(),
                                    self._gettype(), summary, multiid)
                self._v_dsindex += 1


    def _thresholds(self, context, targettype):
        """build the hrule opts for any thresholds that apply to our view"""
        allthreshs = targettype.getThresholds(context) 
        threshs = []
        for thresh in allthreshs:
            for dsname in thresh.dsnames:
                if dsname in self._dsnames:
                    threshs.append(thresh)
                    break
        if threshs: self._v_gopts.append("COMMENT:Data Thresholds:\j")
        for thresh in threshs:
            if thresh.meta_type == 'RRDThreshold':
                minvalue = thresh.getGraphMinval(context)
                if minvalue and minvalue != 'n':
                    minvalue = str(minvalue)
                    minvalue += self._getthreshcolor()
                    self._v_gopts.append("HRULE:%s:%s" % 
                            (minvalue, thresh.getMinLabel(context)))
                maxvalue = thresh.getGraphMaxval(context)
                if maxvalue:
                    maxvalue = str(maxvalue)
                    maxvalue += self._getthreshcolor()
                    self._v_gopts.append("HRULE:%s:%s" % 
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

InitializeClass(RRDView)
