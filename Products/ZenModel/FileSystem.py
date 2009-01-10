###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""FileSystem

FileSystem is a file system on a server

$Id: FileSystem.py,v 1.12 2004/04/06 22:33:23 edahl Exp $"""

__version__ = "$Revision: 1.12 $"[11:-2]
from Globals import DTMLFile
from Globals import InitializeClass

from Products.ZenUtils.Utils import convToUnits
from Products.ZenRelations.RelSchema import *

from OSComponent import OSComponent
from Products.ZenUtils.Utils import prepId
from Products.ZenWidgets import messaging

from Products.ZenModel.ZenossSecurity import *

def manage_addFileSystem(context, id, userCreated, REQUEST=None):
    """make a filesystem"""
    fsid = prepId(id)
    fs = FileSystem(fsid)
    context._setObject(fsid, fs)
    fs = context._getOb(fsid)
    fs.mount = id
    if userCreated: fs.setUserCreateFlag()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()+'/manage_main')

addFileSystem = DTMLFile('dtml/addFileSystem',globals())

class FileSystem(OSComponent):
    """
    FileSystem object
    """

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

    _properties = OSComponent._properties + (
        {'id':'mount', 'type':'string', 'mode':''},
        {'id':'storageDevice', 'type':'string', 'mode':''},
        {'id':'type', 'type':'string', 'mode':''},
        {'id':'blockSize', 'type':'int', 'mode':''},
        {'id':'totalBlocks', 'type':'long', 'mode':''},
        {'id':'totalFiles', 'type':'long', 'mode':''},
        {'id':'maxNameLen', 'type':'int', 'mode':''},
        )
    _relations = OSComponent._relations + (
        ("os", ToOne(ToManyCont, "Products.ZenModel.OperatingSystem", "filesystems")),
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
                , 'permissions'   : (ZEN_VIEW,)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (ZEN_VIEW, )
                },
                { 'id'            : 'perfConf'
                , 'name'          : 'Template'
                , 'action'        : 'objTemplates'
                , 'permissions'   : ("Change Device", )
                },                
                { 'id'            : 'viewHistory'
                , 'name'          : 'Modifications'
                , 'action'        : 'viewHistory'
                , 'permissions'   : (ZEN_VIEW_MODIFICATIONS,)
                },
            )
          },
        )

    
    def totalBytes(self):
        """
        Return the total bytes of a filesytem
        """
        return int(self.blockSize) * int(self.totalBlocks)


    def totalBytesString(self):
        """
        Return the number of total bytes in human readable from ie 10MB
        """
        return convToUnits(self.totalBytes())


    def usedBytes(self):
        """
        Return the number of used bytes on a filesytem.
        """
        blocks = self.usedBlocks()
        if blocks is not None:
            return self.blockSize * blocks
        return None


    def usedBytesString(self):
        """
        Return the number of used bytes in human readable form ie 10MB
        """
        __pychecker__='no-constCond'
        ub = self.usedBytes()
        return ub is None and "unknown" or convToUnits(ub)


    def availBytes(self):
        """
        Return the number of availible bytes for this filesystem
        """
        blocks = self.usedBlocks()
        if blocks is not None:
            return self.blockSize * (self.totalBlocks - self.usedBlocks())
        return None


    def availBytesString(self):
        """
        Return the number of availible bytes in human readable form ie 10MB
        """
        __pychecker__='no-constCond'
        ab = self.availBytes()
        return ab is None and "unknown" or convToUnits(ab)


    def availFiles(self):
        """
        Not implemented returns 0
        """
        return 0


    def capacity(self):
        """
        Return the percentage capacity of a filesystems using its rrd file
        """
        __pychecker__='no-returnvalues'
        usedBytes = self.usedBytes()
        if self.totalBytes() and usedBytes is not None:
            return int(100.0 * self.usedBytes() / self.totalBytes())
        return 'unknown'


    def inodeCapacity(self):
        """
        Not implemented returns 0
        """
        return 0


    def usedBlocks(self, default = None):
        """
        Return the number of used blocks stored in the filesystem's rrd file
        """
        blocks = self.cacheRRDValue('usedBlocks', default)
        if blocks is not None:
            return long(blocks)
        elif self.blockSize:
            # no usedBlocks datapoint, so this is probably a Windows device
            # using perfmon for data collection and therefore we'll look for
            # the freeMegabytes datapoint
            freeMB = self.cacheRRDValue('freeMegabytes', default)
            if freeMB is not None:
                usedBytes = self.totalBytes() - long(freeMB) * 1024 * 1024
                return usedBytes / self.blockSize
        return None


    def usedBlocksString(self):
        """
        Return the number of used blocks in human readable form ie 10MB
        """
        __pychecker__='no-constCond'
        ub = self.usedBlocks()
        return ub is None and "unknown" or convToUnits(ub)


    def getRRDNames(self):
        """
        Return the datapoint name of this filesystem 'usedBlocks_usedBlocks'
        """
        return ['usedBlocks_usedBlocks']


    def viewName(self): 
        """
        Return the mount point name of a filesystem '/boot'
        """
        return self.mount
    name = viewName


    def manage_editFileSystem(self, monitor=False,
                mount=None, storageDevice=None, 
                type=None, blockSize=None, 
                totalFiles=None, maxNameLen=None, 
                snmpindex=None, REQUEST=None):
        """
        Edit a Service from a web page.
        """
        if mount:
            self.mount = mount
            self.storageDevice = storageDevice
            self.type = type
            self.blockSize = blockSize
            self.totalFiles = totalFiles
            self.maxNameLen = maxNameLen
            self.snmpindex = snmpindex

        self.monitor = monitor
        self.index_object()

        if REQUEST:
            messaging.IMessageSender(self).sendToBrowser(
                'Filesystem Updated',
                'Filesystem %s was edited.' % self.id
            )
            return self.callZenScreen(REQUEST)


InitializeClass(FileSystem)
