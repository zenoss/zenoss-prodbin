#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""HardDisk

HardDisk is a collection of devices and subsystems that make
up a business function

$Id: HardDisk.py,v 1.7 2004/04/06 22:33:24 edahl Exp $"""

__version__ = "$Revision: 1.7 $"[11:-2]

from Globals import Persistent
from Globals import DTMLFile
from Globals import InitializeClass

from DeviceComponent import DeviceComponent

def manage_addHardDisk(context, id, title = None, REQUEST = None):
    """make a filesystem"""
    hd = HardDisk(id, title)
    context._setObject(id, hd)
    hd = context._getOb(id)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addHardDisk = DTMLFile('dtml/addHardDisk',globals())


class HardDisk(DeviceComponent):
    """HardDisk object"""

    portal_type = meta_type = 'HardDisk'

    manage_editHardDiskForm = DTMLFile('dtml/manageEditHardDisk',globals())
    
    _properties = (
                 {'id':'description', 'type':'string', 'mode':''},
                 {'id':'snmpindex', 'type':'int', 'mode':''},
                 {'id':'hostresindex', 'type':'int', 'mode':''},
                )    

    def __init__(self, id, title = None): 
        DeviceComponent.__init__(self, id, title)
        self.description = ""
        self.snmpindex = 0
        self.hostresindex = 0

    def viewName(self): return self.description


InitializeClass(HardDisk)
