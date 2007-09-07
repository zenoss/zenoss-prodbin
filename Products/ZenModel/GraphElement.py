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

class GraphElement(ZenModelRM):
    
    meta_type = 'GraphElement'
    
    deviceId = ''
    componentPath = ()
    graphId = ''
    sequence = 0
    
    _properties = ZenModelRM._properties + (
    )

    _relations =  (
        ("graphReport", 
            ToOne(ToManyCont,"Products.ZenModel.GraphReport", "elements")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'editGraphReport',
            'actions'        :
            ( 
                {'name'          : 'Report',
                'action'        : 'viewGraphReport',
                'permissions'   : ("View",),
                },
                {'name'          : 'Edit',
                'action'        : 'editGraphReport',
                'permissions'   : ("Manage DMD",),
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def __init__(self, id, component, graph, sequence, 
                    title=None, buildRelations=None):
        ZenModelRM.__init__(self, id, title, buildRelations)
        device = component.device()
        self.deviceId = device.id
        self.componentPath = component.getPrimaryPath()[
                                                len(device.getPrimaryPath()):]
        self.graphId = graph.id
        self.sequence = sequence
        
    
    def getComponentDesc(self, dmd):
        comp = self.getComponent(dmd)
        if comp:
            desc = '/'.join(comp.getPrimaryPath() + self.componentPath)
        else:
            desc = '%s: missing' % self.deviceId
        return desc

        
    def getComponent(self, dmd):
        component = dmd.Devices.findDevice(self.deviceId)
        for part in self.componentPath:
            component = getattr(component, part)
        return component


    def getGraphUrl(self, dmd, drange):
        component = self.getComponent(dmd)
        graph = get
        component.getGraphDefUrl(g, drange, template)


InitializeClass(GraphElement)
