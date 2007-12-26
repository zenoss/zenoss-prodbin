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

__doc__="""CommentGraphPoint

Handles GraphPoints that define an rrd COMMENT
"""

from GraphPoint import GraphPoint
from Globals import InitializeClass

def manage_addCommentGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = CommentGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class CommentGraphPoint(GraphPoint):

    meta_type = 'CommentGraphPoint'

    text = ''

    _properties = GraphPoint._properties + (
        {'id':'text', 'type':'string', 'mode':'w'},
        )

    def getDescription(self):
        return self.text


    def getType(self):
        return 'COMMENT'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(cmds, context, rrdDir, addSummary, idx, multiid, prefix)
        return cmds + ['COMMENT:%s' % self.text.replace(':', '\:')]


InitializeClass(CommentGraphPoint)
