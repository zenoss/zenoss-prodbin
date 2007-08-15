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

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from ZenModelRM import ZenModelRM
from Products.ZenRelations.RelSchema import *

class GraphReportElement(ZenModelRM):
    
    meta_type = 'GraphReportElement'
    
    deviceId = ''
    componentPath = ()
    graphId = ''
    sequence = 0
        
    _properties = ZenModelRM._properties + (
    )

    _relations =  ZenModelRM._relations + (
        ("report", 
            ToOne(ToManyCont,"Products.ZenModel.GraphReport", "elements")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'editGraphReportElement',
            'actions'        :
            ( 
                {'name'          : 'Edit',
                'action'        : 'editGraphReportElement',
                'permissions'   : ("Manage DMD",),
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def __init__(self, id, component, graph, sequence, 
                    title=None, buildRelations=True):
        ZenModelRM.__init__(self, id, title, buildRelations)
        device = component.device()
        self.deviceId = device.id
        self.componentPath = component.getPrimaryPath()[
                                                len(device.getPrimaryPath()):]
        self.graphId = graph.id
        self.sequence = sequence
    
    
    def getDesc(self):
        return '%s    %s' % (self.graphId, self.getComponentDesc())
        
    
    def getComponentDesc(self):
        comp = self.getComponent()
        if comp:
            parts = [''] + list(comp.getPrimaryPath()[3:]) \
                            + list(self.componentPath)
            desc = '/'.join(parts)
        else:
            desc = '%s: missing' % self.deviceId
        return desc

        
    def getComponent(self):
        component = self.dmd.Devices.findDevice(self.deviceId)
        for part in self.componentPath:
            component = getattr(component, part)
        return component
        
        
    def getGraph(self):
        graph = self.getComponent().getGraph(self.graphId)
        return graph


    def getGraphUrl(self, drange=None):
        component = self.getComponent()
        graph = component.getGraph(self.graphId)
        return component.getRRDGraphUrl(graph, drange, graph.rrdTemplate())


InitializeClass(GraphReportElement)
