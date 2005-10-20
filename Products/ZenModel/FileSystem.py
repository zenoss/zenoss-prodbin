#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

__doc__="""FileSystem

FileSystem is a file system on a server

$Id: FileSystem.py,v 1.12 2004/04/06 22:33:23 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from DeviceComponent import DeviceComponent

def manage_addFileSystem(context, id, REQUEST = None):
    """make a filesystem"""
    fs = FileSystem(id)
    context._setObject(id, fs)
    fs = context._getOb(id)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addFileSystem = DTMLFile('dtml/addFileSystem',globals())


class FileSystem(DeviceComponent):
    """FileSystem object"""

    portal_type = meta_type = 'FileSystem'

    manage_editFileSystemForm = DTMLFile('dtml/manageEditFileSystem',globals())
    
    _properties = (
        {'id':'mount', 'type':'string', 'mode':''},
        {'id':'storageDevice', 'type':'string', 'mode':''},
        {'id':'type', 'type':'string', 'mode':''},
        {'id':'blockSize', 'type':'int', 'mode':''},
        {'id':'totalBytes', 'type':'long', 'mode':''},
        {'id':'usedBytes', 'type':'long', 'mode':''},
        {'id':'availBytes', 'type':'long', 'mode':''},
        {'id':'totalFiles', 'type':'long', 'mode':''},
        {'id':'availFiles', 'type':'long', 'mode':''},
        {'id':'capacity', 'type':'int', 'mode':''},
        {'id':'inodeCapacity', 'type':'int', 'mode':''},
        {'id':'maxNameLen', 'type':'int', 'mode':''},
        {'id':'snmpindex', 'type':'int', 'mode':''},
        )
    _relations = DeviceComponent._relations + (
        ("server", ToOne(ToManyCont, "Server", "filesystems")),
        )
    

    factory_type_information = ( 
        { 
            'id'             : 'FileSystem',
            'meta_type'      : 'FileSystem',
            'description'    : """Arbitrary device grouping class""",
            'icon'           : 'FileSystem_icon.gif',
            'product'        : 'ZenModel',
            'factory'        : 'manage_addFileSystem',
            'immediate_view' : 'viewFileSystem',
            'actions'        :
            ( 
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'viewFileSystem'
                , 'permissions'   : ('View',)
                },
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ('View',)
                },
            )
          },
        )


    def __init__(self, id, title = None): 
        DeviceComponent.__init__(self, id, title)
        self.mount = ""
        self.storageDevice = ""
        self.type = ""
        self.blockSize = 0
        self.totalBytes = 0
        self.usedBytes = 0
        self.availBytes = 0
        self.totalFiles = 0
        self.availFiles = 0
        self.capacity = 0
        self.inodeCapacity = 0
        self.maxNameLen = 0
        self.snmpindex = 0

    def viewName(self): return self.mount

InitializeClass(FileSystem)
