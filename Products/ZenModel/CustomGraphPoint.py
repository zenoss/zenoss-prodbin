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

__doc__="""CustomGraphPoint

Handles GraphPoints that define rrdtool CDEF's and VDEF's
"""

from GraphPoint import GraphPoint
from AccessControl import ClassSecurityInfo, Permissions
from Products.ZenRelations.RelSchema import *


class CustomGraphPoint(GraphPoint):

    meta_type = 'CustomGraphPoint'

    customTypes = ('CDEF', 'VDEF')
    customType = 'CDEF'
    
    
    _properties = GraphPoint._properties + (
        {'id':'customType', 'type':'selection', 
        'select_variable' : 'customTypes', 'mode':'w'},
        )
    
    factory_type_information = ( 
    { 
        'immediate_view' : 'editCustomGraphPoint',
        'actions'        :
        ( 
            { 'id'            : 'edit'
            , 'name'          : 'Graph Point'
            , 'action'        : 'editCustomGraphPoint'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    security = ClassSecurityInfo()

    def __init__(self, id, title=None, buildRelations=True):
        GraphPoint.__init__(self, id, title, buildRelations)


    def getDescription(self):
        return self.id


    def getType(self):
        return 'Custom %s' % self.customType


    def graphOpts(self, file, summary, index, multiid=-1):
        ''' Build the graphing commands for this graphpoint
        '''
        # Ignoring multiid for now because I'm unconvinced it applies to custom
        # graphpoints or how to handle the situation if it does.
        assert(multiid == -1)
        
        graph = []
        
        # Create the base DEF
        graph.append("%s:%s=%s" % (self.customType, self.id, self.rpn))


        # Actually draw the line or area
        if self.draw:
            graph.append('%s:%s#%s:%s' % (
                        self.lineType or DEFAULT_LINE,
                        self.id,
                        (self.color or self.getDefaultColor(index)).lstrip('#'),
                        self.id.rjust(14),
                        ))
            # Add summary
            if summary:
                graph.extend(self._summary(self.id, self.format, ongraph=1))
            
        return graph
