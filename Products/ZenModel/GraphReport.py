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
from GraphReportElement import GraphReportElement
from Products.ZenUtils.ZenTales import talesCompile, getEngine
from DateTime import DateTime

def manage_addGraphReport(context, id, REQUEST = None):
    ''' Create a new GraphReport
    '''
    gr = GraphReport(id)
    context._setObject(gr.id, gr)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


class GraphReport(ZenModelRM):

    meta_type = "GraphReport"
    
    numColumns = 1
    numColumnsOptions = (1, 2, 3)
    comments = (
        '<div style="float: right;"><img src="img/onwhitelogo.png"></div>\n'
        '<div style="font-size: 16pt;">${report/id}</div>\n'
        '<div style="font-size:12pt;">${now/aDay} ${now/aMonth} ${now/day},'
        ' ${now/year}<br />\n'
        '${now/AMPMMinutes}\n'
        '</div>\n'
        '<div style="clear: both" />')

    _properties = ZenModelRM._properties + (
        {'id':'comments', 'type':'text', 'mode':'w'},
        {'id':'numColumns', 'type':'int', 
            'select_variable' : 'numColumnOptions', 'mode':'w'},
    )

    _relations =  (
        ("elements", 
            ToManyCont(ToOne,"Products.ZenModel.GraphReportElement", "report")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'viewGraphReport',
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


    def getBreadCrumbUrlPath(self):
        '''
        Return the url to be used in breadcrumbs for this object.
        '''
        return self.getPrimaryUrlPath() + '/editGraphReport'

    def getThing(self, deviceId, componentPath):
        ''' Return either a device or a component, or None if not found
        '''
        thing = self.dmd.Devices.findDevice(deviceId)
        if thing and componentPath:
            parts = componentPath.split('/')
            for part in parts:
                thing = getattr(thing, part)
        return thing


    security.declareProtected('Manage DMD', 'manage_addGraphElement')
    def manage_addGraphElement(self, deviceIds=(), componentPaths=(), 
                            graphIds=(), REQUEST=None):
        ''' Add a new graph report element
        '''
        def GetId(deviceId, componentPath, graphId):
            component = componentPath.split('/')[-1]
            parts = [p for p in (deviceId, component, graphId) if p]
            root = ' '.join(parts)
            candidate = self.prepId(root)
            i = 2
            while candidate in self.elements.objectIds():
                candidate = self.prepId('%s-%s' % (root, i))
                i += 1
            return candidate

        msg = ''
        if isinstance(deviceIds, basestring):
            deviceIds = list(deviceIds)
        if isinstance(componentPaths, basestring):
            componentPaths = list(componentPaths)
        componentPaths = componentPaths or ('')
        for devId in deviceIds:
            for cPath in componentPaths:
                thing = self.getThing(devId, cPath)
                if thing:
                    for graphId in graphIds:
                        graph = thing.getGraphDef(graphId)
                        if graph:            
                            newId = GetId(devId, cPath, graphId)
                            ge = GraphReportElement(newId)
                            ge.deviceId = devId
                            ge.componentPath = cPath
                            ge.graphId = graphId
                            ge.sequence = len(self.elements())
                            self.elements._setObject(ge.id, ge)
            
        if REQUEST:
            if msg:
                REQUEST['message'] = msg
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_deleteGraphReportElements')
    def manage_deleteGraphReportElements(self, ids=(), REQUEST=None):
        ''' Delete elements from this report
        '''
        for id in ids:
            self.elements._delObject(id)
        self.manage_resequenceGraphReportElements()
        if REQUEST:
            REQUEST['message'] = 'Graph%s deleted' % (len(ids)>1 and 's' or '')
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 
                                    'manage_resequenceGraphReportElements')
    def manage_resequenceGraphReportElements(self, seqmap=(), origseq=(), 
                                    REQUEST=None):
        """Reorder the sequecne of the graphs.
        """
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.elements(), seqmap, origseq, REQUEST)
    

    security.declareProtected('View', 'getComments')
    def getComments(self):
        ''' Returns tales-evaluated comments
        '''
        compiled = talesCompile('string:' + self.comments)
        e = {'rpt': self, 'report': self, 'now':DateTime()}
        result = compiled(getEngine().getContext(e))
        if isinstance(result, Exception):
            result = 'Error: %s' % str(result)
        return result


    # def getGraphs(self, drange=None):
    #     """get the default graph list for this object"""
    #     def cmpGraphs(a, b):
    #         return cmp(a['sequence'], b['sequence'])
    #     graphs = []
    #     for element in self.elements():
    #         graphs.append({
    #             'title': element.getDesc(),
    #             'url': element.getGraphUrl(),
    #             'sequence': element.sequence,
    #             })
    #     graphs.sort(cmpGraphs)
    #     return graphs
    
    
    def getElements(self):
        """get the ordered elements
        """
        def cmpElements(a, b):
            return cmp(a.sequence, b.sequence)
        elements = [e for e in self.elements()]
        elements.sort(cmpElements)
        return elements


InitializeClass(GraphReport)
