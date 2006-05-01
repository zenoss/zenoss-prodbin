#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""FileSystem

FileSystem is a file system on a server

$Id: FileSystem.py,v 1.12 2004/04/06 22:33:23 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]

import locale

from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent

def manage_addFileSystem(context, id, REQUEST = None):
    """make a filesystem"""
    fs = FileSystem(id)
    context._setObject(id, fs)
    fs = context._getOb(id)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main') 

addFileSystem = DTMLFile('dtml/addFileSystem',globals())


class FileSystem(OSComponent):
    """FileSystem object"""

    portal_type = meta_type = 'FileSystem'

    manage_editFileSystemForm = DTMLFile('dtml/manageEditFileSystem',globals())
    
    mount = ""
    storageDevice = ""
    type = ""
    blockSize = 0
    totalBlocks = 0L
    totalFiles = 0L
    capacity = 0
    inodeCapacity = 0
    maxNameLen = 0

    _properties = (
        {'id':'mount', 'type':'string', 'mode':''},
        {'id':'storageDevice', 'type':'string', 'mode':''},
        {'id':'type', 'type':'string', 'mode':''},
        {'id':'blockSize', 'type':'int', 'mode':''},
        {'id':'totalBlocks', 'type':'long', 'mode':''},
        {'id':'totalFiles', 'type':'long', 'mode':''},
        {'id':'maxNameLen', 'type':'int', 'mode':''},
        )
    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont, "OperatingSystem", "filesystems")),
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
                { 'id'            : 'perfConf'
                , 'name'          : 'PerfConf'
                , 'action'        : 'objRRDTemplate'
                , 'permissions'   : ("Change Device", )
                },                
                { 'id'            : 'viewHistory'
                , 'name'          : 'Changes'
                , 'action'        : 'viewHistory'
                , 'permissions'   : ('View',)
                },
            )
          },
        )

    
    def totalBytes(self):
        return self.blockSize * self.totalBlocks

    def totalBytesString(self):
        return locale.format("%d", self.totalBytes(), True)

    def usedBytes(self):
        return self.blockSize * self.usedBlocks()

    def availBytes(self):
        return self.blockSize * (self.totalBlocks - self.usedBlocks())

    def availFiles(self):
        return 0

    def capacity(self):
        return int(100.0 * self.usedBytes() / self.totalBytes())

    def inodeCapacity(self):
        return 0

    def usedBlocks(self):
        return long(self.cacheRRDValue('usedBlocks'))

    def getRRDNames(self):
        return ['usedBlocks']

    def viewName(self): return self.mount

InitializeClass(FileSystem)
