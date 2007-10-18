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

__doc__="""VruleGraphPoint

Handles GraphPoints that define an rrd VRULE
"""

import os
from GraphPoint import GraphPoint
from Globals import InitializeClass


def manage_addVruleGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = VruleGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class VruleGraphPoint(GraphPoint):

    meta_type = 'VruleGraphPoint'

    time = 0
    color = ''
    legend = GraphPoint.DEFAULT_LEGEND

    _properties = GraphPoint._properties + (
        {'id':'time', 'type':'integer', 'mode':'w'},
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'legend', 'type':'string', 'mode':'w'},
        )
    
    def getDescription(self):
        return '%s %s %s' % (self.time, self.color, self.legend)


    def getType(self):
        return 'VRULE'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        if not self.time:
            return cmds
        gopts = 'VRULE:%s%s' % (self.time, self.getColor(idx))
        if self.legend:
            legend = self.talesEval(self.legend, context)
            legend = self.escapeForRRD(legend)
            gopts += ':%s' % legend
        return cmds + [gopts]


InitializeClass(VruleGraphPoint)
