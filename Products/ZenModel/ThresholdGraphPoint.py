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

__doc__="""ThreshGraphPoint

Handles GraphPoints that refer to RRDDataPoints
"""

from GraphPoint import GraphPoint


class ThresholdGraphPoint(GraphPoint):

    meta_type = 'ThresholdGraphPoint'
  
    isThreshold = True
  
    threshId = ''
    color = ''
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'threshId', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )
    
    def getThreshClass(self, context):
        ''' Get the related threshold class or None if it doesn't exist
        '''
        threshClass = None
        if self.graphDef.rrdTemplate():
            threshClass = getattr(self.graphDef.rrdTemplate.thresholds, 
                                        self.threshId, None)
        elif self.graphDef.report() and None:
            for temp in context.getRRDTemplates():
                threshClass = getattr(temp.thresholds, self.threshId, None)
                if threshClass:
                    break
        return threshClass


    def getDescription(self):
        return self.threshId


    def getType(self):
        return 'Threshold'


    # def getMissingDPNames(self):
    #     ''' Return a list of datapoint names that are used by this threshold
    #     but not included in any graphpoint.
    #     '''
    #     threshClass = self.getThreshClass()
    #     if threshClass:
    #         dpNames = [dpName for dpName in threshClass.dsnames
    #                     if not self.graphDef.isDataPointGraphed(dpName)]
    #     else:
    #         dpNames = []
    #     return dpNames
    
        
    def getRelatedGraphPoints(self, context):
        ''' Return a dictionary where keys are the dp names from the
        threshold and values are a DataPointGraphPoint for that dp or
        None if a RPGP doesn't exist.  If multiple exist for any given
        dp then return just the first one.
        '''
        from DataPointGraphPoint import DataPointGraphPoint
        related = {}
        threshClass = self.getThreshClass(context)
        if threshClass:
            for dpName in threshClass.dsnames:
                gps = self.graphDef.getDataPointGraphPoints(dpName)
                if gps:
                    gp = gps[0]
                else:
                    gp = None
                related[dpName] = gp
        return related


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        relatedGps = self.getRelatedGraphPoints(context)
        gopts = []
        threshClass = self.getThreshClass(context)
        if threshClass:
            threshInst = threshClass.createThresholdInstance(context)
            namespace = self.addPrefix(prefix, self.id)
            color = self.getThresholdColor(idx)
            template = self.graphDef.rrdTemplate() or None
            # We can't get templates when doing mgr
            # need to refactor threshinst to not take template.
            # Looks like it's not being used anyway.
            gopts = threshInst.getGraphElements(
                        template, gopts, namespace, 
                        color, relatedGps)
        return cmds + gopts
