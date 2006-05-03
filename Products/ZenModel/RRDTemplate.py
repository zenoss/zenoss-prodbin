#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
from Acquisition import aq_parent

from ZenModelRM import ZenModelRM

from Products.ZenRelations.RelSchema import *


def manage_addRRDTemplate(context, id, REQUEST = None):
    """make a RRDTemplate"""
    tt = RRDTemplate(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDTemplate = DTMLFile('dtml/addRRDTemplate',globals())


def crumbspath(templ, crumbs):
    """Create the crumbs path for sub objects of an RRDTemplate.
    """
    dc = templ.deviceClass() 
    pt = "/perfConfig"
    if not dc: 
       dc = templ.getPrimaryParent()
       pt = "/objRRDTemplate"
    url = dc.getPrimaryUrlPath()+pt
    del crumbs[-2]
    crumbs.insert(-1,(url,'PerfConf'))
    return crumbs



class RRDTemplate(ZenModelRM):

    meta_type = 'RRDTemplate'

    security = ClassSecurityInfo()
  
    description = ""

    _properties = (
        {'id':'description', 'type':'text', 'mode':'w'},
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

    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(RRDTemplate, self).breadCrumbs(terminator)
        return crumbspath(self, crumbs)


    def isEditable(self, context):
        """Is this template editable in context.
        """
        return (self.isManager() and 
                (context == self or context.isLocalName(self.id)))

    
    def getGraphs(self):
        """Return our graphs objects in proper order.
        """
        graphs = self.graphs()
        graphs.sort(lambda x, y: cmp(x.sequence, y.sequence))
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
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    def callZenScreen(self, REQUEST):
        """Redirect to primary parent object if this template is locally defined
        """
        if REQUEST.get('zenScreenName',"") == "objRRDTemplate":
            return self.getPrimaryParent().callZenScreen(REQUEST)
        return super(RRDTemplate, self).callZenScreen(REQUEST)


    def manage_deleteRRDDataSources(self, ids=(), REQUEST=None):
        """Delete RRDDataSources from this DeviceClass 
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            if getattr(self.datasources,id,False):
                self.datasources._delObject(id)
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    security.declareProtected('Add DMD Objects', 'manage_addRRDThreshold')
    def manage_addRRDThreshold(self, id, REQUEST=None):
        """Add an RRDThreshold to this DeviceClass.
        """
        from RRDThreshold import RRDThreshold
        if not id: return self.callZenScreen(REQUEST)
        org = RRDThreshold(id)
        self.thresholds._setObject(org.id, org)
        if REQUEST: 
            return self.callZenScreen(REQUEST)
            

    def manage_deleteRRDThresholds(self, ids=(), REQUEST=None):
        """Delete RRDThresholds from this DeviceClass 
        """
        if not ids: return self.callZenScreen(REQUEST)
        for id in ids:
            if getattr(self.thresholds,id,False):
                self.thresholds._delObject(id)
        if REQUEST: 
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_addRRDGraph')
    def manage_addRRDGraph(self, id="", REQUEST=None):
        """Add an RRDGraph to our RRDTemplate.
        """
        from RRDGraph import RRDGraph
        nextseq = 0
        graphs = self.getGraphs()
        if len(graphs) > 0:
            nextseq = graphs[-1].sequence + 1
        if id:
            graph = RRDGraph(id)
            graph.sequence = nextseq
            self.graphs._setObject(graph.id, graph)
        if REQUEST:
            return self.callZenScreen(REQUEST)
        

    security.declareProtected('Manage DMD', 'manage_deleteRRDGraphs')
    def manage_deleteRRDGraphs(self, ids=(), REQUEST=None):
        """Remove an RRDGraph from this RRDTemplate.
        """
        for id in ids:
            self.graphs._delObject(id)
            self.manage_resequenceRRDGraphs()
        if REQUEST:
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_resequenceRRDGraphs')
    def manage_resequenceRRDGraphs(self, seqmap=(), REQUEST=None):
        """Reorder the sequecne of the RRDGraphs.
        """
        if seqmap:
            for i, graph in enumerate(self.getGraphs()):
                graph.sequence = seqmap[i]
        for i, graph in enumerate(self.getGraphs()):
            graph.sequence = i
        if REQUEST:
            return self.callZenScreen(REQUEST)

        

InitializeClass(RRDTemplate)
