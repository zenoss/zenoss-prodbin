#################################################################
#
#   Copyright (c) 2003 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""RRDDataSource

Defines attributes for how a datasource will be graphed
and builds the nessesary DEF and CDEF statements for it.

$Id: RRDDataSource.py,v 1.6 2003/06/03 18:47:49 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import os

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Globals import DTMLFile
from OFS.PropertyManager import PropertyManager

from RRDToolItem import RRDToolItem
import utils

def manage_addRRDDataSource(context, id, REQUEST = None):
    """make a RRDDataSource"""
    ds = RRDDataSource(id)
    context._setObject(ds.id, ds)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')
                                     

addRRDDataSource = DTMLFile('dtml/addRRDDataSource',globals())


class RRDDataSourceError(Exception): pass

class RRDDataSource(RRDToolItem, PropertyManager):

    meta_type = 'RRDDataSource'
  
    rrdtypes = ('', 'COUNTER', 'GAUGE', 'DERIVE')
    linetypes = ('', 'AREA', 'LINE')
    
    manage_options = PropertyManager.manage_options + \
                     RRDToolItem.manage_options
    _properties = (
                 {'id':'oid', 'type':'string', 'mode':'w'},
                 {'id':'rrdtype', 'type':'selection',
                    'select_variable' : 'rrdtypes', 'mode':'w'},
                 {'id':'isrow', 'type':'boolean', 'mode':'w'},
                 {'id':'rpn', 'type':'string', 'mode':'w'},
                 {'id':'rrdmax', 'type':'long', 'mode':'w'},
                 {'id':'limit', 'type':'long', 'mode':'w'},
                 {'id':'linetype', 'type':'selection', 
                    'select_variable' : 'linetypes', 'mode':'w'},
                 {'id':'color', 'type':'string', 'mode':'w'},
                 {'id':'format', 'type':'string', 'mode':'w'},
                )


    def __init__(self, id):
        self.id = utils.prefixid(self.meta_type, id)
        self.oid = ''
        self.rrdtype = 'COUNTER'
        self.isrow = True
        self.rpn = ""
        self.rrdmax = -1
        self.color = ""
        self.linetype = 'LINE'
        self.limit = -1
        self.format = '%0.2lf%s'


    def textload(self, args):
        """called by RRDLoader to populate a RRDDataSource"""
        utils.loadargs(self, args) 
        if self.oid.split('.')[-1] == "0":
            self.isrow = False

        
    def graphOpts(self, file, defaultcolor, defaulttype, summary, multiid=-1):
        """build graph options for this datasource"""
        
        if self.getIndex() == -1: 
            raise "DataSourceError", "Not part of a TargetType"
        graph = []
        src = "ds%d" % self.getIndex()
        dest = src
        if multiid != -1: dest += str(multiid)
        graph.append("DEF:%s=%s:%s:AVERAGE" % (dest, file, src))
        src = dest

        if self.rpn: 
            dest = "rpn%d" % self.getIndex()
            if multiid != -1: dest += str(multiid)
            graph.append("CDEF:%s=%s,%s" % (dest, src, self.rpn))
            src = dest

        if self.limit > 0:
            dest = "limit%d" % self.getIndex()
            if multiid != -1: dest += str(multiid)
            graph.append("CDEF:%s=%s,%s,GT,UNKN,%s,IF"%
                        (dest,src,self.limit,src))
            src = dest

        if not self.color: src += defaultcolor
        else: src += self.color
        
        if not self.linetype: type = defaulttype
        else: type = self.linetype

        if multiid != -1:
            fname = os.path.basename(file)
            if fname.find('.rrd') > -1: fname = fname[:-4]
            name = "%s-%s" % (self.getName(), fname)
        else: name = self.getName()

        graph.append(":".join((type, src, name,)))

        if summary:
            src,color=src.split('#')
            graph.extend(self._summary(src, self.format, ongraph=1))
        return graph

   
    def summary(self, file, format="%0.2lf%s"):
        """return only arguments to generate summary"""
        if self.getIndex() == -1: 
            raise "DataSourceError", "Not part of a TargetType"
        graph = []
        src = "ds%d" % self.getIndex()
        dest = src
        graph.append("DEF:%s=%s:%s:AVERAGE" % (dest, file, src))
        src = dest

        if self.rpn: 
            dest = "rpn%d" % self.getIndex()
            graph.append("CDEF:%s=%s,%s" % (dest, src, self.rpn))
            src = dest

        graph.extend(self._summary(src, self.format, ongraph=1))
        return graph

    
    def _summary(self, src, format="%0.2lf%s", ongraph=1):
        """Add the standard summary opts to a graph"""
        gopts = []
        funcs = ("LAST", "AVERAGE", "MAX")
        tags = ("cur\:", "avg\:", "max\:")
        for i in range(len(funcs)):
            label = "%s%s" % (tags[i], format)
            gopts.append(self.summElement(src, funcs[i], label, ongraph))
        gopts[-1] += "\j"
        return gopts

    
    def summElement(self, src, function, format="%0.2lf%s", ongraph=1):
        """Make a single summary element"""
        if ongraph: opt = "GPRINT"
        else: opt = "PRINT"
        return ":".join((opt, src, function, format))
        

    def setIndex(self, index):
        self._v_index = index


    def getIndex(self):
        if not hasattr(self, '_v_index'):
            self._v_index = -1
        return self._v_index
