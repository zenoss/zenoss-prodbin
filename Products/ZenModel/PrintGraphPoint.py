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

__doc__="""PrintGraphPoint

Handles GraphPoints that define an rrd PRINT
"""

from GraphPoint import GraphPoint
from Globals import InitializeClass


def manage_addPrintGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = PrintGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class PrintGraphPoint(GraphPoint):

    meta_type = 'PrintGraphPoint'

    vname = ''
    format = ''
    strftime = ''

    _properties = GraphPoint._properties + (
        {'id':'vname', 'type':'string', 'mode':'w'},
        {'id':'format', 'type':'string', 'mode':'w'},
        {'id':'strftime', 'type':'string', 'mode':'w'},
        )

    def getDescription(self):
        return self.format


    def getType(self):
        return 'PRINT'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, rrdDir)
        return cmds + ['PRINT:%s:%s%s' % (
                    self.addPrefix(prefix, self.vname),
                    (self.format or self.DEFAULT_FORMAT).replace(':', '\:'),
                    self.strftime and ':%s' % self.strftime or '')]


InitializeClass(PrintGraphPoint)
