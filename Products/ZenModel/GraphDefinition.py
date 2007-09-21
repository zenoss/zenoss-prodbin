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

__doc__="""GraphDefinition

GraphDefinition defines the global options for a graph.
"""

import re
import sys
from sets import Set
import string

from Products.ZenRelations.RelSchema import *
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from GraphPoint import GraphPoint
from ZenModelRM import ZenModelRM
from ZenPackable import ZenPackable
from OFS.ObjectManager import checkValidId as globalCheckValidId
import logging
log = logging.getLogger("zen.Device")


def manage_addGraphDefinition(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    if REQUEST:
        REQUEST['message'] = 'That operation is not supported.'
        self.callZenScreen(REQUEST)

class FakeContext:
    def __init__(self, name):
        self.id = name
    def __getattr__(self, name):
        return FakeContext(name)
    def __call__(self, *kw, **args):
        return self
    def __getitem__(self, key):
        return FakeContext(key)
    def __str__(self):
        return self.id
    def device(self):
        return self
    def __nonzero__(self):
        return True
    def rrdPath(self):
        return 'rrdPath'

class GraphDefinition(ZenModelRM, ZenPackable):
    '''
    '''
    
    meta_type = 'GraphDefinition'
   
    height = 100
    width = 500
    units = ""
    log = False
    base = False
    #summary = True
    miny = -1
    maxy = -1
    custom = ""
    hasSummary = True
    sequence = 0

    _properties = (
        {'id':'height', 'type':'int', 'mode':'w'},
        {'id':'width', 'type':'int', 'mode':'w'},
        {'id':'units', 'type':'string', 'mode':'w'},
        {'id':'log', 'type':'boolean', 'mode':'w'},
        {'id':'base', 'type':'boolean', 'mode':'w'},
        #{'id':'summary', 'type':'boolean', 'mode':'w'},
        {'id':'miny', 'type':'int', 'mode':'w'},
        {'id':'maxy', 'type':'int', 'mode':'w'},
        {'id':'custom', 'type':'text', 'mode':'w'},
        {'id':'hasSummary', 'type':'boolean', 'mode':'w'},
        {'id':'sequence', 'type':'long', 'mode':'w'},
        )

    _relations =  (
        ("rrdTemplate", 
            ToOne(ToManyCont,"Products.ZenModel.RRDTemplate", "graphDefs")),
        ('report',
            ToOne(ToManyCont, 'Products.ZenModel.MultiGraphReport', 'graphDefs')),
        ('graphPoints', 
            ToManyCont(ToOne, 'Products.ZenModel.GraphPoint', 'graphDef')),
        # Remove this relationship after version 2.1
        ('reportClass',
            ToOne(ToManyCont, 'Products.ZenModel.MultiGraphReportClass', 'graphDefs')),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'editGraphDefinition',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Graph Definition'
            , 'action'        : 'editGraphDefinition'
            , 'permissions'   : ( Permissions.view, )
            },
            { 'id'            : 'editCustom'
            , 'name'          : 'Graph Custom Definition'
            , 'action'        : 'editCustGraphDefinition'
            , 'permissions'   : ( Permissions.view, )
            },
            { 'id'            : 'viewCommands'
            , 'name'          : 'Graph Commands'
            , 'action'        : 'viewGraphCommands'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    ## Basic stuff

    def getGraphPoints(self, includeThresholds=True):
        ''' Return ordered list of graph points
        '''
        def cmpGraphPoints(a, b):
            try:
                a = int(a.sequence)
            except ValueError:
                a = sys.maxint
            try:
                b = int(b.sequence)
            except ValueError:
                b = sys.maxint
            return cmp(a, b)
        gps =  [gp for gp in self.graphPoints()
                if includeThresholds or not gp.isThreshold]
        gps.sort(cmpGraphPoints)
        return gps
        
        
    def getThresholdGraphPoints(self):
        ''' Get ordered list of threshold graph points
        '''
        gps = [gp for gp in self.getGraphPoints() if gp.isThreshold]
        return gps


    def isThresholdGraphed(self, threshId):
        ''' Return true if there is a thresholdgraphpoint with threshId=threshid
        '''
        for gp in self.getThresholdGraphPoints():
            if gp.threshId == threshId:
                return True
        return False
        
        
    def isDataPointGraphed(self, dpName):
        ''' Return true if there is at least one graphpoint with a dsName
        equal to dpName.
        '''
        from DataPointGraphPoint import DataPointGraphPoint
        for gp in self.getGraphPoints(includeThresholds=False):
            if isinstance(gp, DataPointGraphPoint):
                if gp.dpName == dpName:
                    return True
        return False
        

    ## GUI Support


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        if self.rrdTemplate():
            from RRDTemplate import crumbspath
            crumbs = super(GraphDefinition, self).breadCrumbs(terminator)
            return crumbspath(self.rrdTemplate(), crumbs, -2)
        return ZenModelRM.breadCrumbs(self, terminator)
        

    def checkValidId(self, id, prep_id = False):
        """Checks a valid id
        """
        # RRD docs say that limit on vnames is 255 characters and that
        # A-Za-z0-9_ are the valid characters.  Zenoss reserves - for it's own
        # use.  Limiting to 200 instead just to leave room for whatever.
        # http://oss.oetiker.ch/rrdtool/doc/rrdgraph_data.en.html
        if len(id) > 200:
            return 'GraphPoint names can not be longer than 200 characters.'
        allowed = Set(list(string.ascii_letters)
                        + list(string.digits)
                        + ['_'])
        attempted = Set(list(id))
        if not attempted.issubset(allowed):
            return 'Only letters, digits and underscores are allowed' + \
                    ' in GraphPoint names.'
        return ZenModelRM.checkValidId(self, id, prep_id)


    def getGraphPointDescriptions(self):
        return [gi.getDescription() for gi in self.graphPoints()]
        
        
    def getGraphPointsNames(self):
        ''' Return list of graph point ids
        '''
        return [gp.id for gp in self.getGraphPoints()]
        
        
    def getGraphPointOptions(self):
        ''' Used by dialog_addGraphPoint to construct the list of 
        available graphpoint types.
        '''
        return (('DefGraphPoint', 'DEF'),
                ('VdefGraphPoint', 'VDEF'),
                ('CdefGraphPoint', 'CDEF'),
                ('PrintGraphPoint', 'PRINT'),
                ('GprintGraphPoint', 'GPRINT'),
                ('CommentGraphPoint', 'COMMENT'),
                ('VruleGraphPoint', 'VRULE'),
                ('HruleGraphPoint', 'HRULE'),
                ('LineGraphPoint', 'LINE'),
                ('AreaGraphPoint', 'AREA'),
                ('TickGraphPoint', 'TICK'),
                ('ShiftGraphPoint', 'SHIFT'))
        

    def createGraphPoint(self, cls, newId):
        ''' Create the graphpoint with the given id or something similar
        and add to self.graphPoints
        '''
        def getUniqueId(container, base):
                ids = container.objectIds()
                new = base
                i = 2
                while new in ids:
                    new = '%s%s' % (base, i)
                    i += 1
                return new
        newId = getUniqueId(self.graphPoints, newId)
        gp = cls(newId)
        if gp.isThreshold:
            gp.sequence = 0
        else:
            gp.sequence = len(self.graphPoints())
        self.graphPoints._setObject(gp.id, gp)
        if gp.id == 0:
            self.manage_resequenceGraphPoints()
        return gp
        

    def manage_addCustomGraphPoint(self, new_id, flavor, REQUEST=None):
        ''' Create a new graphpoint of the given class and id
        '''
        exec 'import %s' % flavor
        cls = eval('%s.%s' % (flavor, flavor))
        gp = self.createGraphPoint(cls, new_id)
        if REQUEST:
            url = '%s/graphPoints/%s' % (self.getPrimaryUrlPath(), gp.id)
            REQUEST['RESPONSE'].redirect(url)
            return self.callZenScreen(REQUEST)
        return gp


    def manage_addDataPointGraphPoints(self, dpNames, includeThresholds=False,
                                                REQUEST=None):
        ''' Create new graph points
        The migrate script graphDefinitions and friends depends on the first
        element in newGps being the DataPointGraphPoint when only one
        name is passed in dpNames.
        '''
        from DataPointGraphPoint import DataPointGraphPoint
        from ThresholdGraphPoint import ThresholdGraphPoint
        newGps = []
        for dpName in dpNames:
            gp = self.createGraphPoint(DataPointGraphPoint, dpName)
            gp.dpName = dpName
            newGps.append(gp)
        if includeThresholds:
            for dpName in dpNames:
                newGps += self.addThresholdsForDataPoint(dpName)
        if REQUEST:
            REQUEST['message'] = '%s Graph Point%s added' % (len(newGps),
                len(newGps) > 1 and 's' or '')
            return self.callZenScreen(REQUEST)
        return newGps
        
        
    def addThresholdsForDataPoint(self, dpName):
        ''' Make sure that Threshold graph points exist for all thresholds
        that use the given dpName.
        Return a list of all graphpoints created by this call.
        '''
        from ThresholdGraphPoint import ThresholdGraphPoint
        newGps = []
        for thresh in self.rrdTemplate().thresholds():
            if thresh.canGraph(self) \
                    and dpName in thresh.dsnames \
                    and not self.isThresholdGraphed(thresh.id):
                gp = self.createGraphPoint(ThresholdGraphPoint, thresh.id)
                gp.threshId = thresh.id
                newGps.append(gp)
        return newGps


    def manage_addThresholdGraphPoints(self, threshNames, REQUEST=None):
        ''' Create new graph points
        '''         
        from ThresholdGraphPoint import ThresholdGraphPoint
        newGps = []
        for threshName in threshNames:
            #thresh = getattr(self.rrdTemplate.thresholds, threshName)
            gp = self.createGraphPoint(ThresholdGraphPoint, threshName)
            gp.threshId = threshName
            newGps.append(gp)
        if REQUEST:
            REQUEST['message'] = '%s Graph Point%s added' % (len(newGps),
                len(newGps) > 1 and 's' or '')
            return self.callZenScreen(REQUEST)
        return newGps
            

    def manage_deleteGraphPoints(self, ids=(), REQUEST=None):
        ''' Deleted given graphpoints
        '''
        num = 0
        for id in ids:
            if getattr(self.graphPoints, id, False):
                num += 1
                self.graphPoints._delObject(id)
            self.manage_resequenceGraphPoints()
        if REQUEST:
            REQUEST['message'] = 'Deleted %s GraphPoint%s' % (
                num, num > 1 and 's' or '')
            return self.callZenScreen(REQUEST)


    def manage_resequenceGraphPoints(self, seqmap=(), origseq=(), REQUEST=None):
        """Reorder the sequence of the GraphPoints.
        """
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.graphPoints(), 
                            seqmap, origseq, REQUEST)


    def getDataPointOptions(self):
        ''' Return a list of (value, name) tuples for the list of datapoints
        which the user selects from to create new graphpoints.
        '''
        return [(dp.name(), dp.name()) 
                    for dp in self.rrdTemplate.getRRDDataPoints()]


    def getThresholdOptions(self):
        ''' Return a list of (value, name) tuples for the list of thresholds
        which the user selects from to create new graphpoints.
        '''
        return [(t.id, t.id) for t in self.rrdTemplate.thresholds()] 


    def getTalesContext(self):
        ''' Standard stuff to add to context for tales expressions
        '''
        return { 'graphDef': self }


    ## Graphing Support


    def getGraphCmds(self, context, rrdDir, multiid=-1, upToPoint=None,
            includeSetup=True, includeThresholds=True, 
            prefix='', cmds=None, idxOffset=0):
        """build the graph opts for a single rrdfile"""
        from Products.ZenUtils.ZenTales import talesEval
        if not cmds:
            cmds = []
        if includeSetup:
            cmds += self.graphsetup()

        # Have to draw thresholds before data so that thresholds won't
        # obscure data (especially if threshold uses TICK)
        if includeThresholds:
            threshGps = [gp for gp in self.getThresholdGraphPoints()
                        if upToPoint is None or gp.sequence < upToPoint]
            if threshGps:
                cmds.append("COMMENT:Data Thresholds\j")
                for index, gp in enumerate(threshGps):
                    cmds = gp.getGraphCmds(cmds, context, rrdDir,
                                        self.hasSummary, index+idxOffset,
                                        multiid, prefix)

        gpList = [gp for gp in self.getGraphPoints(includeThresholds=False)
                    if upToPoint is None or gp.sequence < upToPoint]
        for index, gp in enumerate(gpList):
            cmds = gp.getGraphCmds(cmds, context, rrdDir, 
                                        self.hasSummary, index+idxOffset,
                                        multiid, prefix)
        if self.custom and includeSetup \
            and not upToPoint:
            res = talesEval("string:"+self.custom, context)
            res = [l for l in res.split('\n') if l.strip()]
            cmds.extend(res)
            #if self.hasSummary:
            #    cmds = self.addSummary(cmds)

        return cmds


    def getRRDVariables(self, upToPoint=None):
        ''' Return list of rrd variable names that are defined by DEF, CDEF
        or VDEF statements in the rrd commands.  If upToPoint is not None then
        only consider statements generated by graphoints where
        sequence < upToPoint
        '''
        cmds = self.getFakeGraphCmds(upToPoint=upToPoint)
        names = [line[line.find(':')+1:line.find('=')]
                    for line in cmds.split('\n')
                    if line[:line.find(':')] in ('DEF', 'CDEF', 'VDEF')]
        return names

        
    def getFakeGraphCmds(self, upToPoint=None):
        ''' Used to display the graph commands (or a reasonable likeness)
        to the user
        '''
        context = FakeContext('Context')
        cmds = self.getGraphCmds(context, context.rrdPath(), upToPoint=upToPoint)
        cmds = '\n'.join(cmds)
        return cmds


    def graphsetup(self):
        """Setup global graph parameters.
        """
        gopts = ['-F', '-E']
        if self.height:
            gopts.append('--height=%d' % self.height)
        if self.width:
            gopts.append('--width=%d' % self.width)
        if self.log:
            gopts.append('--logarithmic')
        if self.maxy > -1:
            gopts.append('--upper-limit=%d' % self.maxy)
            gopts.append('--rigid')
        if self.miny > -1:
            gopts.append('--lower-limit=%d' % self.miny)
            gopts.append('--rigid')
        if self.units: 
            gopts.append('--vertical-label=%s' % self.units)
            if self.units == 'percentage':
                if not self.maxy > -1:
                    gopts.append('--upper-limit=100')
                if not self.miny > -1:
                    gopts.append('--lower-limit=0')
        if self.base:
            gopts.append('--base=1024')
        gopts = [str(o) for o in gopts]
        return gopts


    def getDataPointGraphPoints(self, dpName):
        ''' Return a list of DataPointGraphPoints that use the given dpName
        '''
        from DataPointGraphPoint import DataPointGraphPoint
        return [gp for gp in self.graphPoints()
                if isinstance(gp, DataPointGraphPoint)
                and gp.dpName == dpName]
        
        


    # security.declareProtected('Manage DMD', 'getUniqueDpNames')
    # def getUniqueDpNames(self):
    #     ''' Get a list of all unique datapoint names
    #     '''
    #     from sets import Set
    #     dpNames = Set()
    #     for t in self.dmd.Devices.getAllRRDTemplates():
    #         for ds in t.datasources():
    #             for dp in ds.datapoints():
    #                 dpNames.add(dp.name())
    #         if len(dpNames) > 100:
    #             break
    #     dpNames = list(dpNames)
    #     dpNames.sort()
    #     return dpNames

    # def buildCustomDS(self, cmds, rrdDir, template):
    #     """Build a list of DEF statements for the dpNames in this graph.
    #     Their variable name will be dsname.  These can then be used in a 
    #     custom statement.
    #     """
    #     for dsname in self.dpNames:
    #         dp = template.getRRDDataPoint(dsname)
    #         if dp is None: continue
    #         myfile = os.path.join(rrdfile, dp.name()) + ".rrd"
    #         gopts.append('DEF:%s=%s:ds0:AVERAGE' % (dp.name(), myfile))
    #     return gopts
                
    # gelement = re.compile("^LINE|^AREA|^STACK", re.I).search
    # def addSummary(self, gopts):
    #     """Add summary labels for all graphed elements in gopts.
    #     Used for custom graphs
    #     """
    #     vars = [o.split(":",2)[1].split("#")[0] for o in gopts if self.gelement(o)]
    # 
    #     pad = max([len(v) for v in vars] + [0])
    #     for var in vars: 
    #         gopts = self.dataSourceSum(gopts, var, pad=pad)
    #     return gopts
            

    # def dataSourceSum(self, gopts, src, pad=0, format="%0.2lf%s", ongraph=1):
    #     """Add the standard summary opts to a graph for variable src.
    #     VDEF:src_last=src,LAST 
    #     GPRINT:src_last:cur\:%0.2lf%s 
    #     VDEF:src_avg=src,AVERAGE
    #     GPRINT:src_avg:avg\:%0.2lf%s
    #     VDEF:src_max=src,MAXIMUM 
    #     GPRINT:src_max:max\:%0.2lf%s\j
    #     """
    #     funcs = (("cur\:", "LAST"), ("avg\:", "AVERAGE"), ("max\:", "MAXIMUM"))
    #     for tag, func in funcs:
    #         label = "%s%s" % (tag, format)
    #         if pad:
    #             label = label.ljust(pad)
    #         vdef = "%s_%s" % (src,func.lower())
    #         gopts.append("VDEF:%s=%s,%s" % (vdef,src,func))
    #         opt = ongraph and "GPRINT" or "PRINT"
    #         gopts.append("%s:%s:%s" % (opt, vdef, label))
    #     gopts[-1] += "\j"
    #     return gopts

InitializeClass(GraphDefinition)
