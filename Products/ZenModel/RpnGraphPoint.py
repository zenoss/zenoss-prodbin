###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""RpnGraphPoint

Base class for graph points with RPNs. Never directly instantiated.
"""

from Globals import InitializeClass

from Products.ZenModel.GraphPoint import GraphPoint
from Products.ZenRRD.utils import rpnStack


class RpnGraphPoint(GraphPoint):
    rpn = ''

    _properties = GraphPoint._properties + (
        {'id':'rpn', 'type':'string', 'mode':'w'},
        )
    
    def getDescription(self):
        return self.rpn


    def getRpn(self, multiid=-1, prefix=''):
        parts = self.rpn.split(',')
        for i, var in enumerate(parts):
            try:
                unused = float(var)
                continue
            except ValueError:
                pass

            if var in rpnStack.opcodes:
                continue
                
            parts[i] = self.getDsName(var, multiid, prefix)

        return ','.join(parts)


InitializeClass(RpnGraphPoint)
