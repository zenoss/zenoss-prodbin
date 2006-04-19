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

    def getRRDDataSources(self):
        """Return data sources for this template.
        """
        return [self.getRRDDataSource(dsname) for dsname in self.dsnames]


    def getRRDDataSourceNames(self):
        """Return list of data source names used on this object.
        """
        return [ ds for ds in self.getPrimaryParent().getRRDDataSourceNames() \
                    if ds in self.dsnames ]

        
    def getAvailRRDDataSourceNames(self):
        """Return list of availible data source names not used on this object.
        """
        return [ ds for ds in self.getPrimaryParent().getRRDDataSourceNames() \
                    if ds not in self.dsnames ]

        
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
   

    def manage_addRRDDataSource(self, id="", REQUEST=None):
        """Add a data source name to our dsnames list.
        """
        if id and id not in self.dsnames:
            if not self.dsnames: self.dsnames = []
            self.dsnames.append(id)
            self._p_changed = 1
        if REQUEST:
            return self.callZenScreen(REQUEST)


    def manage_deleteRRDDataSources(self, ids=(), REQUEST=None):
        """Remove a a list of dsnames from our dsnames list.
        """
        for id in ids:
            try: 
                self.dsnames.remove(id)
                self._p_changed = True
            except ValueError: pass 
        if REQUEST:
            return self.callZenScreen(REQUEST)


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
