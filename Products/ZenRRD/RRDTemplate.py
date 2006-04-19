#################################################################
#
#   Copyright (c) 2003 Zenoss, Inc. All rights reserved.
#
#################################################################

from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from RRDToolItem import RRDToolItem

import utils
from Products.ZenRelations.RelSchema import *


def manage_addRRDTemplate(context, id, REQUEST = None):
    """make a RRDTemplate"""
    tt = RRDTemplate(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDTemplate = DTMLFile('dtml/addRRDTemplate',globals())


class RRDTemplate(RRDToolItem):

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


    def textload(self, args):
        """called by RRDLoader to populate TargetType datasources and graphs
        args should have camma separated list of dsnames and graphs"""
        utils.loadargs(self, args) 
    

    def getGraphs(self):
        """Return our graphs objects in proper order.
        """
        graphs = self.graphs()
        graphs.sort(cmp(x.sequence, y.sequence))
        return graphs 




InitializeClass(RRDTemplate)
