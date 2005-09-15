#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""SnmpAttMap

manages a map of snmp oids to attributes in a class

$Id: SnmpAttMap.py,v 1.1 2002/06/14 11:22:00 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]


from Globals import DTMLFile
from OFS.SimpleItem import SimpleItem

from SnmpPropertyManager import SnmpPropertyManager

def manage_addSnmpAttMap(context, id, title = None, REQUEST = None):
    """make a SnmpAttMap"""
    d = SnmpAttMap(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addSnmpAttMap = DTMLFile('dtml/addSnmpAttMap',globals())

class SnmpAttMap(SnmpPropertyManager, SimpleItem):
    """SnmpAttMap object"""
    meta_type = 'SnmpAttMap'
    manage_options = (SnmpPropertyManager.manage_options + SimpleItem.manage_options)
    _properties = ()

    def __init__(self, id, title = None, 
                relationshipName='', tableOid='', description = ''):
        self.id = id
        self.title = title
        self._oidmap = {}

    def getOidMap(self):
        return self._oidmap
