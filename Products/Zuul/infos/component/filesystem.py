###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements
from Products.Zuul.interfaces import IFileSystemInfo
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.component import ComponentInfo


class FileSystemInfo(ComponentInfo):
    implements(IFileSystemInfo)

    mount = ProxyProperty('mount')
    storageDevice = ProxyProperty('storageDevice')
    type = ProxyProperty('type')
    blockSize = ProxyProperty('blockSize')
    totalBlocks = ProxyProperty('totalBlocks')
    totalFiles = ProxyProperty('totalFiles')
    maxNameLength = ProxyProperty('maxNameLen')

    @property
    def totalBytes(self):
        return self._object.totalBytes()

    @property
    def usedBytes(self):
        return self._object.usedBytes()

    @property
    def availableBytes(self):
        return self._object.availableBytes()

    @property
    def capacityBytes(self):
        return self._object.capacity()

    @property
    def availableFiles(self):
        return self._object.availableFiles()

    @property
    def capacityFiles(self):
        return self._object.inodeCapacity()


