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

class GraphReport(ZenModelRM):

    meta_type = "GraphReport"

    _properties = ZenModelRM._properties + (
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
    def manage_addGraphElement(self, deviceId='', componentPath='', graphIds=(), 
                                                            REQUEST=None):
        ''' Add a new graph report element
        '''
        def GetId(deviceId, componentPath, graphId):
            root = '%s-%s-%s' % (deviceId, '/'.join(componentPath), graphId)
            candidate = self.prepId(root)
            i = 2
            while candidate in self.elements.objectIds():
                candidate = self.prepId('%s-%s' % (root, i))
                i += 1
            return candidate

        msg = ''
        thing = self.getThing(deviceId, componentPath)
        if thing:
            for graphId in graphIds:
                graph = thing.getGraph(graphId)
                if graph:            
                    newId = GetId(deviceId, componentPath, graphId)
                    ge = GraphReportElement(newId, thing, graph, 
                                            len(self.elements()))
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
            REQUEST['message'] = 'Graph%s deleted' % len(ids) > 1 and 's' or ''
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 
                                    'manage_resequenceGraphReportElements')
    def manage_resequenceGraphReportElements(self, seqmap=(), origseq=(), 
                                    REQUEST=None):
        """Reorder the sequecne of the graphs.
        """
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.elements(), seqmap, origseq, REQUEST)
    

    security.declareProtected('Manage DMD', 'selectDevice')
    def selectDevice(self, REQUEST=None):
        ''' Do nothing for now
        '''
        return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'selectComponent')
    def selectComponent(self, REQUEST=None):
        ''' Do nothing for now
        '''
        return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'getFilteredDeviceList')
    def getFilteredDeviceList(self, filter=''):
        ''' Return list of devices matching the device filter field
        '''
        def cmpDevice(a, b):
            return cmp(a.id, b.id)
        if filter:
            devices = self.dmd.Devices.searchDevices(filter)
        else:
            devices = self.dmd.Devices.getSubDevices()
        devices.sort(cmpDevice)
        return devices


    def getComponentOptions(self, deviceId):
        ''' Return options for the component selection list
        '''
        d = self.dmd.Devices.findDevice(deviceId)
        if d:
            dPathLen = len(d.getPrimaryId()) + 1
            comps = d.getMonitoredComponents()
            paths = [c.getPrimaryId()[dPathLen:] for c in comps]
            return paths
        return []


    def getAvailableGraphs(self, deviceId, componentPath=''):
        ''' Return the graph ids of the given device/component
        '''
        graphs = []
        thing = self.getThing(deviceId, componentPath)
        if thing:
            for t in thing.getRRDTemplates():
                graphs += t.getGraphs()
        return graphs


    def getGraphs(self, drange=None):
        """get the default graph list for this object"""
        def cmpGraphs(a, b):
            return cmp(a['sequence'], b['sequence'])
        graphs = []
        for element in self.elements():
            graphs.append({
                'title': element.getDesc(),
                'url': element.getGraphUrl(),
                'sequence': element.sequence,
                })
        graphs.sort(cmpGraphs)
        return graphs


InitializeClass(GraphReport)
