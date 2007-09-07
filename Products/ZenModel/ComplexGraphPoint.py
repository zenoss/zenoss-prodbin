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

__doc__="""ComplexGraphPoint

"""

import os

from GraphPoint import GraphPoint                                     

class ComplexGraphPoint(GraphPoint):

    lineTypeOptions = (
        ('Not Drawn', ''),
        ('Line', 'LINE'),
        ('Area', 'AREA'),
        )

    color = ''
    lineType = 'LINE'
    lineWidth = 1
    stacked = False
    format = GraphPoint.DEFAULT_FORMAT

    _properties = GraphPoint._properties + (
        {'id':'color', 'type':'string', 'mode':'w'},
        {'id':'lineType', 'type':'selection', 
        'select_variable' : 'lineTypes', 'mode':'w'},
        {'id':'lineWidth', 'type':'long', 'mode':'w'},
        {'id':'stacked', 'type':'boolean', 'mode':'w'},
        {'id':'format', 'type':'string', 'mode':'w'},
        )



