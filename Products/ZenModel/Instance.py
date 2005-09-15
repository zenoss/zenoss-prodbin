#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""Instance

base class for all confmon data objects.

$Id: Instance.py,v 1.26 2003/04/10 19:52:47 edahl Exp $"""

__version__ = "$Revision: 1.26 $"[11:-2]

import types

from AccessControl import ClassSecurityInfo
from OFS.History import Historical
from DateTime import DateTime
from Globals import DTMLFile
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Globals import InitializeClass

from ConfmonBase import ConfmonBase
from CricketView import CricketView

class Instance(ConfmonBase, CricketView, Historical): 
    """Base class for all confmon classes"""

    meta_type = 'Instance'

    #need to figure out how to make this an action
    #index_html = PageTemplateFile('skins/devices/deviceIndex.pt',globals())
    

    manage_options = (ConfmonBase.manage_options[:2] + 
                        Historical.manage_options +
                        ConfmonBase.manage_options[2:])

    security = ClassSecurityInfo()
    
    def __init__(self, id, title=None):
        ConfmonBase.__init__(self, id, title)
        self._cricketTargetMap = {}
        self._cricketTargetPath = ''

    #====================================================
    # Fist bogus attempt at history diff functions
    #====================================================
    def manage_historyCompare(self, rev1, rev2, REQUEST,
                                historyComparisonResults=''):
        """perform diff of to instance objects"""
        dt1=DateTime(rev1._p_mtime)
        dt2=DateTime(rev2._p_mtime)
        diffdata = self.compareAtts(rev1, rev2)
        hcr = self._maketable(diffdata, dt1, dt2)
        hcr += "<br />"
        #diffdata = self.compareToOneRelations(rev1, rev2)
        #hcr += self._maketable(diffdata, dt1, dt2)
        return Historical.manage_historyCompare(self, rev1, rev2, REQUEST,
                            historyComparisonResults=hcr)

    def _maketable(self, diffdata, dt1, dt2):
        hcr = "<table border='1' cellpadding='3'>\n"
        hcr += "<tr><th>Attribute</th><th>%s</th><th>%s</th></tr>\n" % (dt1, dt2)
        for name, (att1, att2) in diffdata.items():
            hcr = hcr + "<tr><td>" + name + "</td>"
            hcr = hcr + "<td>" + str(att1) + "</td>"
            hcr = hcr + "<td>" + str(att2) + "</td></tr>\n"
        hcr += "</table>\n"
        return hcr

    
    def compareAtts(self, rev1, rev2):
        """walk _properties and look for differences"""
        diffdata = {}
        props = ({'id':'id'}, {'id':'getPrimaryUrlPath',},) + self._properties
        for prop in props:
            pname = prop['id']
            att1 = self._getattr(rev1, pname)
            att2 = self._getattr(rev2, pname)
            #print pname, att1, att2
            if  att1 != att2:
                diffdata[pname] = (att1, att2,)
        return diffdata


    def _getattr(self, obj, prop):
        """get attr data even if it is a callable attribute"""
        att = getattr(obj, prop, "")
        if callable(att):
            att = att()
        return att
        

    def compareToOneRelations(self, rev1, rev2):
        """walk relationships and look for differencees"""
        diffdata = {}
        for rname in self.objectIds('To One Relationship'):
            id1 = self._gettoone(rev1, rname)
            id2 = self._gettoone(rev2, rname)
            if id1 != id2:
                diffdata[name] = (id1, id2)
        return diffdata

    def _gettoone(self, obj, name):
        id = ""
        rel = getattr(obj, name, None)
        rel = self.getObjRevByTime(rel)
        if rel:
            id = rel.obj.id
        return id

    def getObjRevByTime(self, obj):
        """look up a related object that matches another objects timestamp"""
        from OFS.History import historicalRevision
        time = float(obj.bobobase_modification_time())
        revs = self._p_jar.db().history(obj._p_oid, None, 100) #FIXME
        tlast = -1
        for rev in revs:
            tdiff = abs(rev['time'] - time)
            if tlast == -1 or tdiff < tlast:
                tlast = tdiff
            else:
                return historicalRevision(obj, rev['serial']) 

    # FIXME: instances need to filter this as well not sure how yet -EAD
    #def all_meta_types(self, interfaces=None):
    #    return self.getParent().all_meta_types(interfaces)


InitializeClass(Instance)
