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

__doc__='''MultiGraphReportClass

MultiGraphReportClass contain MultiGraphReports.
'''

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from ReportClass import ReportClass
from Products.ZenRelations.RelSchema import *
from ZenossSecurity import ZEN_MANAGE_DMD
from Globals import InitializeClass


def manage_addMultiGraphReportClass(context, id, title = None, REQUEST = None):
    ''' Construct a new MultiGraphreportclass
    '''
    frc = MultiGraphReportClass(id, title)
    context._setObject(id, frc)
    if REQUEST is not None:
        REQUEST['message'] = "Report organizer created"
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addMultiGraphReportClass = DTMLFile('dtml/addMultiGraphReportClass',globals())

class MultiGraphReportClass(ReportClass):

    portal_type = meta_type = "MultiGraphReportClass"

    _relations = ReportClass._relations +  (
        ('graphDefs', 
            ToManyCont(ToOne, 'Products.ZenModel.GraphDefinition', 'reportClass')),
        )
    
    security = ClassSecurityInfo()
    
    def getReportClass(self):
        ''' Return the class to instantiate for new report classes
        '''
        return MultiGraphReportClass


    security.declareProtected('Manage DMD', 'manage_addMultiGraphReport')
    def manage_addMultiGraphReport(self, id, REQUEST=None):
        """Add an MultiGraph report to this object.
        """
        from Products.ZenModel.MultiGraphReport import MultiGraphReport
        fr = MultiGraphReport(id)
        self._setObject(id, fr)
        if REQUEST:
            url = '%s/%s/editMultiGraphReport' % (self.getPrimaryUrlPath(), id)
            REQUEST['RESPONSE'].redirect(url)
        return fr

    
    ### Graph Definitions
         
    security.declareProtected(ZEN_MANAGE_DMD, 'getGraphDefs')
    def getGraphDefs(self):
        ''' Return an ordered list of the graph definitions
        '''
        def cmpGraphDefs(a, b):
            try: a = int(a.sequence)
            except ValueError: a = sys.maxint
            try: b = int(b.sequence)
            except ValueError: b = sys.maxint
            return cmp(a, b)
        graphDefs =  self.graphDefs()[:]
        graphDefs.sort(cmpGraphDefs)
        return graphDefs


    security.declareProtected('Manage DMD', 'manage_addGraphDefinition')
    def manage_addGraphDefinition(self, new_id, REQUEST=None):
        """Add a GraphDefinition 
        """
        from GraphDefinition import GraphDefinition
        graph = GraphDefinition(new_id)
        self.graphDefs._setObject(graph.id, graph)
        if REQUEST:
            url = '%s/graphDefs/%s' % (self.getPrimaryUrlPath(), graph.id)
            REQUEST['RESPONSE'].redirect(url)
        return graph
        

    security.declareProtected('Manage DMD', 'manage_deleteGraphDefinitions')
    def manage_deleteGraphDefinitions(self, ids=(), REQUEST=None):
        """Remove GraphDefinitions 
        """
        for id in ids:
            self.graphDefs._delObject(id)
            self.manage_resequenceGraphDefs()
        if REQUEST:
            if len(ids) == 1:
                REQUEST['message'] = 'Graph %s deleted.' % ids[0]
            elif len(ids) > 1:
                REQUEST['message'] = 'Graphs %s deleted.' % ', '.join(ids)
            return self.callZenScreen(REQUEST)



InitializeClass(MultiGraphReportClass)
