#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""SnmpTableMap

manages a map of a snmp table oid and its columns to a relationship
and its related object attributes

$Id: SnmpTableMap.py,v 1.1 2002/06/14 11:22:00 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]


from Globals import DTMLFile

from SnmpAttMap import SnmpAttMap

def manage_addSnmpTableMap(context, id, title = None, REQUEST = None):
    """make a SnmpTableMap"""
    d = SnmpTableMap(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addSnmpTableMap = DTMLFile('dtml/addSnmpTableMap',globals())

class SnmpTableMap(SnmpAttMap):
    """SnmpTableMap object"""
    meta_type = 'SnmpTableMap'
    _properties = (
                    {'id':'relationshipName', 'type':'string', 'mode':'w'},
                    {'id':'remoteClass', 'type':'string', 'mode':'w'},
                    {'id':'tableOid', 'type':'string', 'mode':'w'},
                   ) 

    def __init__(self, id, title = None, relationshipName='', remoteClass='', tableOid=''):
        SnmpAttMap.__init__(self, id, title)
        self.relationshipName = relationshipName
        self.remoteClass = remoteClass
        self.tableOid = tableOid
