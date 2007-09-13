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

__doc__="""VdefGraphPoint

Handles GraphPoints that define an rrd VDEF
"""

import os

from GraphPoint import GraphPoint


def manage_addVdefGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    if REQUEST:
        REQUEST['message'] = 'That operation is not supported.'
        self.callZenScreen(REQUEST)


class VdefGraphPoint(GraphPoint):

    meta_type = 'VdefGraphPoint'

    rpn = ''

    _properties = GraphPoint._properties + (
        {'id':'rpn', 'type':'string', 'mode':'w'},
        )
    

    def getDescription(self):
        return self.rpn


    def getType(self):
        return 'VDEF'
        

    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                            multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        if not self.rpn:
            return cmds

        return cmds + ['VDEF:%s=%s' % (
                        self.getDsName(self.id, multiid, prefix), self.rpn)]

