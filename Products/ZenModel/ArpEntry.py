#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""ArpEntry

ArpEntry represents a group of devices

$Id: ArpEntry.py,v 1.5 2002/07/19 16:35:17 alex Exp $"""

__version__ = "$Revision: 1.5 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from Instance import Instance

def manage_addArpEntry(context, id, title = None, REQUEST = None):
    """make a ArpEntry"""
    d = ArpEntry(id, title)
    context._setObject(id, d)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addArpEntry = DTMLFile('dtml/addArpEntry',globals())

class ArpEntry(Instance):
    """
    ArpEntry object
    """

    meta_type = 'ArpEntry'

    _properties = (
        {'id':'macAddress', 'type':'string', 'mode':'w'},
        ) 
    _relations = (
        ("device", ToOne(ToManyCont,"Device","arptable")),
        )

    def __init__(self, id, title = None, macAddress = ''):
        Instance.__init__(self, id, title)
        self.macAddress = macAddress

InitializeClass(ArpEntry)
