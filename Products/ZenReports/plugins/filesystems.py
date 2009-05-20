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


import Globals
from Products.ZenReports import Utils, Utilization
from Products.ZenReports.AliasPlugin import AliasPlugin, Column, RRDColumn, \
                                            TalesColumnHandler

class filesystems( AliasPlugin ):
    "The file systems report"

    def getColumns(self):
        ##      alias/dp id : column name
        return [ Column( 'deviceName', TalesColumnHandler( 'device.id' ) ),
                 Column( 'mount', TalesColumnHandler( 'component.mount' ) ),
                 RRDColumn( 'usedBytes', 'usedFilesystemSpace__bytes' ),
                 Column( 'totalBytes', TalesColumnHandler( 'component.totalBytes()' ) ) ]
    
    def getCompositeColumns(self):
        return [ Column( 'availableBytes', TalesColumnHandler('totalBytes - usedBytes') ),
                 Column( 'percentFull', TalesColumnHandler( '100 - float(availableBytes) * 100 / float(totalBytes)' ) ) ]
    
    def getComponentPath(self):
        return 'os/filesystems'

