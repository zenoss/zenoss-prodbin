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

__doc__="""DPGraphPoint

Handles GraphPoints that refer to RRDDataPoints
"""

import os
import os.path
from ComplexGraphPoint import ComplexGraphPoint
from Globals import InitializeClass


def manage_addDataPointGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = DataPointGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class DataPointGraphPoint(ComplexGraphPoint):
    '''
    '''    
    meta_type = 'DataPointGraphPoint'
    
    limit = -1
    rpn = ''
    dpName = ''
    cFunc = 'AVERAGE'

    _properties = ComplexGraphPoint._properties + (
        {'id':'limit', 'type':'long', 'mode':'w'},
        {'id':'rpn', 'type':'string', 'mode':'w'},
        {'id':'dpName', 'type':'string', 'mode':'w'},
        {'id':'cFunc', 'type':'string', 'mode':'w'},
        )

    def getDescription(self):
        ''' return a description
        '''
        return self.dpName


    def dataPointId(self):
        '''
        Return the id of the datapoint, without the datasource name
        '''
        return self.dpName.split('_', 1)[-1]


    def getType(self):
        return 'DataPoint'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        graph = []

        rrdFile = os.path.join(rrdDir, self.dpName) + ".rrd"

        # If we are really drawing the graph (ie we do not have a fake context)
        # then make sure the rrd file actually exists.
        if not getattr(context, 'isFake', False):
            if not os.path.isfile(rrdFile):
                desc = context.device().id
                if context.meta_type != 'Device':
                    desc += ' %s' % context.name()
                desc += ' %s' % self.dpName
                cmds.append('COMMENT:MISSING\: data file for %s' % desc)
                return cmds

        # Create the base DEF
        rawName = self.getDsName('%s-raw' % self.id, multiid, prefix)        
        graph.append("DEF:%s=%s:%s:%s" % (rawName, rrdFile, 'ds0', self.cFunc))

        # If have rpn then create a new CDEF
        if self.rpn: 
            rpnName = self.getDsName('%s-rpn' % self.id, multiid, prefix)
            graph.append("CDEF:%s=%s,%s" % (rpnName, rawName, self.rpn))

        # If have limit then create a new CDEF
        if self.limit > -1:
            src = self.rpn and rpnName or rawName
            limitName = self.getDsName('%s-limit' % self.id, multiid, prefix)
            graph.append("CDEF:%s=%s,%s,GT,UNKN,%s,IF"%
                        (limitName,src,self.limit,src))
                        
        if self.limit > -1:
            src = limitName
        elif self.rpn:
            src = rpnName
        else:
            src = rawName

        # Create a cdef for the munged value        
        graph.append('CDEF:%s=%s' % 
                            (self.getDsName(self.id, multiid, prefix), src))

        # Draw
        if self.lineType != self.LINETYPE_DONTDRAW:
            if multiid != -1:
                fname = os.path.basename(rrdDir)
                if fname.find('.rrd') > -1: fname = fname[:-4]
                legend = "%s-%s" % (self.id, fname)
            else:
                legend = self.talesEval(self.legend, context) or self.id
            legend = self.escapeForRRD(legend)
            drawCmd ='%s:%s%s' % (
                        self.lineType,
                        src,
                        self.getColor(idx))
            drawCmd += ':%s' % legend.ljust(14)
            if self.stacked:
                drawCmd += ':STACK'
            graph.append(drawCmd)
            
            # Add summary
            if addSummary:
                graph.extend(self._summary(src, self.format, ongraph=1))
        
        return cmds + graph


    def _summary(self, src, format="%5.2lf%s", ongraph=1):
        """Add the standard summary opts to a graph"""
        gopts = []
        funcs = ("LAST", "AVERAGE", "MAX")
        tags = ("cur\:", "avg\:", "max\:")
        for i in range(len(funcs)):
            label = "%s%s" % (tags[i], format or self.DEFAULT_FORMAT)
            gopts.append(self.summElement(src, funcs[i], label, ongraph))
        gopts[-1] += "\j"
        return gopts


    def summElement(self, src, function, format="%5.2lf%s", ongraph=1):
        """Make a single summary element"""
        if ongraph: opt = "GPRINT"
        else: opt = "PRINT"
        return ":".join((opt, src, function, format))

    
InitializeClass(DataPointGraphPoint)
