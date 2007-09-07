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

__doc__="""DefGraphPoint

Handles GraphPoints that define an rrd DEF
"""

import os
from GraphPoint import GraphPoint


def manage_addDefGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    if REQUEST:
        REQUEST['message'] = 'That operation is not supported.'
        self.callZenScreen(REQUEST)


class DefGraphPoint(GraphPoint):

    meta_type = 'DefGraphPoint'
    
    rrdFile = ''
    dsName = 'ds0'
    step = ''
    start = ''
    end = ''
    cFunc = 'AVERAGE'
    rFunc = ''
    
    _properties = GraphPoint._properties + (
        {'id':'rrdFile', 'type':'string', 'mode':'w'},
        {'id':'dsName', 'type':'string', 'mode':'w'},
        {'id':'step', 'type':'string', 'mode':'w'},
        {'id':'start', 'type':'string', 'mode':'w'},
        {'id':'end', 'type':'string', 'mode':'w'},
        {'id':'cFunc', 'type':'string', 'mode':'w'},
        {'id':'rFunc', 'type':'string', 'mode':'w'},        
        )
    

    def getDescription(self):
        return '%s %s' % (self.rrdFile, self.dsName)


    def getType(self):
        return 'DEF'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, multiid=-1):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.ZenTales import talesEvalStr
        if not (self.rrdFile and self.dsName and self.cFunc):
            return cmds
        
        extraContext = self.getTalesContext()
        extraContext['rrdDir'] = rrdDir
        rrdFile = talesEvalStr(self.rrdFile, self, extraContext)
            
        dest = self.getDsName(self.id, multiid)
        gopt = 'DEF:%s=%s:%s:%s' % (
                    dest,
                    rrdFile,
                    self.dsName,
                    self.cFunc)
        if self.step:
            gopt += ':step=%s' % self.step
        if self.start:
            start = talesEvalStr(self.start, self, extraContext)
            gopt += ':start=%s' % start.replace(':', '\:')
        if self.end:
            end = talesEvalStr(self.end, self, extraContext)
            gopt += ':end=%s' % end.replace(':', '\:')
        if self.rFunc:
            gopt += ':reduce=%s' % self.rFunc        
        return cmds + [gopt]

