###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""CdefGraphPoint

Handles GraphPoints that define an rrd CDEF
"""

from Globals import InitializeClass

from Products.ZenModel.RpnGraphPoint import RpnGraphPoint


def manage_addCdefGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = CdefGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class CdefGraphPoint(RpnGraphPoint):
    meta_type = 'CdefGraphPoint'


    def getType(self):
        return 'CDEF'


    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx,
                        multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(rrdDir)
        if not self.rpn:
            return cmds
        rpn = self.talesEval(self.rpn, context)
        return cmds + ['CDEF:%s=%s' % (
                        self.getDsName(self.id, multiid, prefix),
                        self.getRpn(multiid, prefix))]


InitializeClass(CdefGraphPoint)
