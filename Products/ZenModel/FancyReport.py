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
from DateTime import DateTime

def manage_addFancyReport(context, id, REQUEST = None):
    ''' Create a new FancyReport
    '''
    gr = FancyReport(id)
    context._setObject(gr.id, gr)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')


class FancyReport(ZenModelRM):

    meta_type = "FancyReport"
    

    _properties = ZenModelRM._properties + (
    )

    _relations =  (
        ("graphGroups", 
            ToManyCont(ToOne,"Products.ZenModel.GraphGroup", "report")),
        )

    factory_type_information = ( 
        { 
            'immediate_view' : 'editFancyReport',
            'actions'        :
            ( 
                {'name'          : 'Report',
                'action'        : 'viewFancyReport',
                'permissions'   : ("View",),
                },
                {'name'          : 'Edit',
                'action'        : 'editFancyReport',
                'permissions'   : ("Manage DMD",),
                },
            )
         },
        )

    security = ClassSecurityInfo()


    security.declareProtected('Manage DMD', 'manage_addGraphGroup')
    def manage_addGraphGroup(self, collectionId, graphDefId, REQUEST=None):
        ''' Add a new graph group
        '''
        def GetId(root):
            i = 2
            while candidate in self.graphGroups.objectIds():
                candidate = self.prepId('%s-%s' % (root, i))
                i += 1
            return candidate
        from GraphGroup import GraphGroup
        newId = GetId('%s - %s' % (collectionId, graphDefId))
        gg = GraphGroup(newId, collectionId, graphDefId)
        gg.sequence = len(self.graphGroups())
        self.graphGroups._setObject(gg.id, gg)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(gg.absolute_url())
            return self.callZenScreen(REQUEST)
        return gg


    security.declareProtected('Manage DMD', 'manage_deleteGraphGroups')
    def manage_deleteGraphGroups(self, ids=(), REQUEST=None):
        ''' Delete graph groups from this report
        '''
        for id in ids:
            self.graphGroups._delObject(id)
        self.manage_resequenceGraphGroups()
        if REQUEST:
            REQUEST['message'] = 'Group%s deleted' % len(ids) > 1 and 's' or ''
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_resequenceGraphGroups')
    def manage_resequenceGraphGroups(self, seqmap=(), origseq=(), REQUEST=None):
        """Reorder the sequence of the groups.
        """
        from Products.ZenUtils.Utils import resequence
        return resequence(self, self.graphGroups(), seqmap, origseq, REQUEST)
    

    def getGraphGroups(self):
        """get the ordered groups
        """
        def cmpGroups(a, b):
            return cmp(a.sequence, b.sequence)
        groups = [g for g in self.graphGroups()]
        groups.sort(cmpGroups)
        return groups
        
        
    security.declareProtected('Manage DMD', 'getCollections')
    def getCollections(self):
        ''' Return an alpha ordered list of available collections
        '''
        def cmpCollections(a, b):
            return cmp(a.id, b.id)
        collections = [c for c in self.collections.objectValues()]
        collections.sort(cmpCollections)
        return collections
        
        
    security.declareProtected('Manage DMD', 'getGraphDefs')
    def getGraphDefs(self):
        ''' Return an alpha ordered list of available graphDefs
        '''
        def cmpGraphDefs(a, b):
            return cmp(a.id, b.id)
        gdefs = [gd for fd in self.graphDefs.objectValues()]
        gdefs.sort(cmpGraphDefs)
        return gdefs


InitializeClass(FancyReport)
