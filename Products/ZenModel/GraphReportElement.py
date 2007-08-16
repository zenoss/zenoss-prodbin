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
from Products.ZenUtils.ZenTales import talesCompile, getEngine


def manage_addGraphReportElement(context, id, REQUEST = None):
    """make a RRDGraph"""
    element = GraphReportElement(id)
    context._setObject(element.id, element)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


class GraphReportElement(ZenModelRM):
    
    meta_type = 'GraphReportElement'
    
    deviceId = ''
    componentPath = ''
    graphId = ''
    sequence = 0
    comments = 'Device: ${dev/id}<br />\nComponent: ${comp/id}<br />\n${graph/id}'
        
    _properties = ZenModelRM._properties + (
        {'id':'deviceId', 'type':'string', 'mode':'w'},
        {'id':'componentPath', 'type':'string', 'mode':'w'},
        {'id':'graphId', 'type':'string', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'comments', 'type':'text', 'mode':'w'},
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
    
    
    def getDesc(self):
        return '%s    %s' % (self.graphId, self.getComponentDesc())
        
    
    def getComponentDesc(self):
        
        if isinstance(self.componentPath, tuple):
            self.componentPath = '/'.join(self.componentPath)
        
        return self.componentPath.split('/')[-1]
        
        comp = self.getComponent()
        if comp:
            parts = [''] + list(comp.getPrimaryPath()[3:]) \
                            + list(self.componentPath)
            desc = '/'.join(parts)
        else:
            desc = '%s: missing' % self.deviceId
        return desc
        
    
    def getComments(self):
        ''' Returns tales-evaluated comments
        '''
        dev = self.getDevice()
        comp = self.getComponent()
        graph = self.getGraph()
        compiled = talesCompile('string:' + self.comments)
        e = {'dev':dev, 'device': dev, 
                'comp': comp, 'component':comp,
                'graph': graph}
        result = compiled(getEngine().getContext(e))
        if isinstance(result, Exception):
            result = 'Error: %s' % str(result)
        return result

        
    def getDevice(self):
        return self.dmd.Devices.findDevice(self.deviceId)


    def getComponent(self):
        component = self.getDevice()
        for part in self.componentPath.split('/'):
            if part:
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
