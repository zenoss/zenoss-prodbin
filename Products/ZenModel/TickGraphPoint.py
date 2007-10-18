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

__doc__="""TickGraphPoint

Handles GraphPoints that define an rrd TICK
"""

import os
from GraphPoint import GraphPoint
from Globals import InitializeClass


def manage_addTickGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = TickGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class TickGraphPoint(GraphPoint):

    meta_type = 'TickGraphPoint'

    vname = ''
    color = ''
    fraction = ''
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'vname', 'type':'string', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'fraction', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )

    def getDescription(self):
        return '%s' % self.fraction


    def getType(self):
        return 'TICK'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        if not self.vname:
            return cmds
            
        legend = self.talesEval(self.legend, context)
        legend = self.escapeForRRD(legend)
        return cmds + ['TICK:%s%s%s%s' % (
                    self.addPrefix(prefix, self.vname),
                    self.getThresholdColor(idx),
                    self.fraction and ':%s' % self.fraction or '',
                    legend and ':%s' % legend or '')]


InitializeClass(TickGraphPoint)
