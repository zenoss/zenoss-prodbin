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
    """make a GraphReportElement
    """
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
    summary = ('Device: ${dev/id}\n'
                '&nbsp;&nbsp;\n'
                'Component: ${comp/id}\n'
                '&nbsp;&nbsp;\n'
                'Graph: ${graph/id}\n')
    comments = ('Device: ${dev/id}<br />\n'
                'Component: ${comp/id}<br />\n'
                '${graph/id}')
        
    _properties = ZenModelRM._properties + (
        {'id':'deviceId', 'type':'string', 'mode':'w'},
        {'id':'componentPath', 'type':'string', 'mode':'w'},
        {'id':'graphId', 'type':'string', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'summary', 'type':'text', 'mode':'w'},
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
        
    def talesEval(self, text):
        dev = self.getDevice()
        if not dev:
            return 'Device %s could not be found' % self.deviceId
        comp = self.getComponent()
        if not comp:
            return 'Component %s could not be found for %s' % (
                        self.componentPath, self.deviceId)
        graph = self.getGraphDef()
        if not graph:
            return 'Graph %s could not be found for %s' % (
                        self.graphId, self.deviceId)
        compiled = talesCompile('string:' + text)
        e = {'dev':dev, 'device': dev, 
                'comp': comp, 'component':comp,
                'graph': graph}
        try:
            result = compiled(getEngine().getContext(e))
            if isinstance(result, Exception):
                result = 'Error: %s' % str(result)
        except Exception, e:
            result = 'Error: %s' %  str(e)
        return result
        
    
    def getSummary(self):
        ''' Returns tales-evaluated summary
        '''
        return self.talesEval(self.summary)

    def getComments(self):
        ''' Returns tales-evaluated comments
        '''
        return self.talesEval(self.comments)

        
    def getDevice(self):
        return self.dmd.Devices.findDevice(self.deviceId)


    def getComponent(self):
        component = self.getDevice()
        for part in self.componentPath.split('/'):
            if part:
                component = getattr(component, part, None)
                if not component:
                    break
        return component


    def getGraphDef(self):
        graphDef = self.getComponent().getGraphDef(self.graphId)
        return graphDef


    def getGraphUrl(self, drange=None):
        ''' Return the url for the graph
        '''
        url = ''
        component = self.getComponent()
        if component:
            graph = component.getGraphDef(self.graphId)
            if graph:
                url = component.getGraphDefUrl(graph, drange, graph.rrdTemplate())
        return url


InitializeClass(GraphReportElement)
