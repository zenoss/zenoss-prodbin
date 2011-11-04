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

__doc__="""VdefGraphPoint

Handles GraphPoints that define an rrd VDEF
"""

from Globals import InitializeClass

from Products.ZenModel.RpnGraphPoint import RpnGraphPoint
from Products.ZenUtils.deprecated import deprecated

@deprecated
def manage_addVdefGraphPoint(context, id, REQUEST = None):
    ''' This is here so than zope will let us copy/paste/rename
    graphpoints.
    '''
    gp = VdefGraphPoint(id)
    context._setObject(gp.id, gp)
    if REQUEST:
        return context.callZenScreen(REQUEST)


class VdefGraphPoint(RpnGraphPoint):
    meta_type = 'VdefGraphPoint'


    def getType(self):
        return 'VDEF'
        

    def getGraphCmds(self, cmds, context, rrdDir, addSummary, idx, 
                            multiid=-1, prefix=''):
        ''' Build the graphing commands for this graphpoint
        '''
        from Products.ZenUtils.Utils import unused
        unused(multiid, prefix, rrdDir)
        if not self.rpn:
            return cmds
        rpn = self.talesEval(self.rpn, context)
        return cmds + ['VDEF:%s=%s' % (
                        self.getDsName(self.id, multiid, prefix),
                        self.getRpn(multiid, prefix))]


InitializeClass(VdefGraphPoint)
