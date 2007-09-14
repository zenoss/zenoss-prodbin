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

__doc__='''FancyReportClass

FancyReportClass contain FancyReports.
'''

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from ReportClass import ReportClass
from Products.ZenRelations.RelSchema import *
from ZenossSecurity import ZEN_MANAGE_DMD
from Globals import InitializeClass


def manage_addFancyReportClass(context, id, title = None, REQUEST = None):
    ''' Construct a new fancyreportclass
    '''
    frc = FancyReportClass(id, title)
    context._setObject(id, frc)
    if REQUEST is not None:
        REQUEST['message'] = "Report organizer created"
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addFancyReportClass = DTMLFile('dtml/addFancyReportClass',globals())

class FancyReportClass(ReportClass):

    portal_type = meta_type = "FancyReportClass"

    sub_meta_types = ('FancyReportClass', 'FancyReport')

    _relations = ReportClass._relations +  (
        ('graphDefs', 
            ToManyCont(ToOne, 'Products.ZenModel.GraphDefinition', 'reportClass')),
        )
    
    security = ClassSecurityInfo()

    def manage_addReportClass(self, id, title = None, REQUEST = None):
        ''' Create a new fancy report class
        '''
        import pdb; pdb.set_trace()
        dc = FancyReportClass(id, title)
        self._setObject(id, dc)
        if REQUEST:
            REQUEST['message'] = "Report organizer created"
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_addFancyReport')
    def manage_addFancyReport(self, id, REQUEST=None):
        """Add an fancy report to this object.
        """
        from Products.ZenModel.FancyReport import FancyReport
        fr = FancyReport(id)
        self._setObject(id, fr)
        if REQUEST:
            url = '%s/%s/editFancyReport' % (self.getPrimaryUrlPath(), id)
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



InitializeClass(FancyReportClass)
