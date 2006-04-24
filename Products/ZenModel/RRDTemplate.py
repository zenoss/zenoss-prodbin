#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions

from ZenModelRM import ZenModelRM

from Products.ZenRelations.RelSchema import *


def manage_addRRDTemplate(context, id, REQUEST = None):
    """make a RRDTemplate"""
    tt = RRDTemplate(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDTemplate = DTMLFile('dtml/addRRDTemplate',globals())


class RRDTemplate(ZenModelRM):

    meta_type = 'RRDTemplate'

    security = ClassSecurityInfo()
  
    dsnames = []

    _properties = (
        {'id':'dsnames', 'type':'lines', 'mode':'w'},
        )

    _relations =  (
        ("deviceClass", ToOne(ToManyCont,"RRDTemplate", "rrdTemplates")),
        ("datasources", ToManyCont(ToOne,"RRDDataSource", "rrdTemplate")),
        ("graphs", ToManyCont(ToOne,"RRDGraph", "rrdTemplate")),
        ("thresholds", ToManyCont(ToOne,"RRDThreshold", "rrdTemplate")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = ( 
    { 
        'immediate_view' : 'viewRRDTemplate',
        'actions'        :
        ( 
            { 'id'            : 'overview'
            , 'name'          : 'Overview'
            , 'action'        : 'viewRRDTemplate'
            , 'permissions'   : ( Permissions.view, )
            },
        )
    },
    )

    def getGraphs(self):
        """Return our graphs objects in proper order.
        """
        graphs = self.graphs()
        #FIXME need to sequence graphs
        #graphs.sort(lambda x, y: cmp(x.sequence, y.sequence))
        return graphs 


    def getRRDPath(self):
        """Return the path on which this template is defined.
        """
        return self.getPrimaryParent().getPrimaryDmdId(subrel="rrdTemplates")
   

    def getRRDDataSourceNames(self):
        """Return the list of all datasource names.
        """
        return self.datasources.objectIds()

    
    def getRRDDataSources(self):
        """Return a list of all datasources on this template.
        """
        return self.datasources.objectValues()


    def getRRDDataSource(self, name):
        """Return a datasource based on its name.
        """
        return self.datasources._getOb(name)


    security.declareProtected('Add DMD Objects', 'manage_addRRDDataSource')
    def manage_addRRDDataSource(self, id, REQUEST=None):
        """Add an RRDDataSource to this DeviceClass.
        """
        from RRDDataSource import RRDDataSource
        if not id: return self.callZenScreen(REQUEST)
        org = RRDDataSource(id)
        self.datasources._setObject(org.id, org)
        if REQUEST: return self.callZenScreen(REQUEST)
            

    def manage_deleteRRDDataSources(self, ids=(), REQUEST=None):
        """Delete RRDDataSources from this DeviceClass 
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            if getattr(self.datasources,id,False):
                self.datasources._delObject(id)
        if REQUEST: return self.callZenScreen(REQUEST)


    def manage_addRRDGraph(self, id="", REQUEST=None):
        """Add an RRDGraph to our RRDTemplate.
        """
        from RRDGraph import RRDGraph
        if id:
            graph = RRDGraph(id)
            self.graphs._setObject(graph.id, graph)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        

    def manage_deleteRRDGraphs(self, ids=(), REQUEST=None):
        """Remove an RRDGraph from this RRDTemplate.
        """
        for id in ids:
            self.graphs._delObject(id)
        if REQUEST:
            return self.callZenScreen(REQUEST)


InitializeClass(RRDTemplate)
