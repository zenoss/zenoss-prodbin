#################################################################
#
#   Copyright (c) 2003 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""RRDRelativeThresh

RRDRelativeThresh is the zentinel version of a cricket relative threshold.
In cricket the threshold will look something like this:

ifInOctets:relation:<10 pct:::300:SNMP

for each data source defined

$Id: RRDRelativeThresh.py,v 1.2 2003/11/13 22:52:42 edahl Exp $"""

__version__ = "$Revision: 1.2 $"[11:-2]


from AccessControl import ClassSecurityInfo
from Globals import InitializeClass

from Globals import DTMLFile

from RRDThreshold import RRDThreshold

def manage_addRRDRelativeThresh(context, id, REQUEST = None):
    """make a RRDRelativeThresh"""
    tt = RRDRelativeThresh(id)
    context._setObject(tt.id, tt)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

addRRDRelativeThresh = DTMLFile('dtml/addRRDRelativeThresh',globals())


class RRDRelativeThresh(RRDThreshold):
    
    meta_type = 'RRDRelativeThresh'
   
    security = ClassSecurityInfo()

    operators = (">", "<")

    _properties = (
                 {'id':'dsnames', 'type':'lines', 'mode':'w'},
                 {'id':'delta', 'type':'int', 'mode':'w'},
                 {'id':'operator', 'type':'selection', 
                    'select_variable': 'operators', 'mode':'w'},
                 {'id':'percent', 'type':'boolean', 'mode':'w'},
                 {'id':'timeoffset', 'type':'int', 'mode':'w'},
                )

    _dsnames = []
    delta = 0
    operator = ">"
    percent = 1
    timeoffset = 300
    
    def getCricketThresholds(self, context):
        """return the cricket threshold string that this threshold defines"""
        threshs = []
        for ds in self._dsnames:
            if self.delta:
                value = "%s%s" % (self.operator, self.delta)
                if self.percent: value += " pct"
                thresh = "%s:relation:%s:::%s:SNMP" % (ds,value,self.timeoffset)
                threshs.append(thresh)
        return ','.join(threshs)

InitializeClass(RRDRelativeThresh)
