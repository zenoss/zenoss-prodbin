##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import Globals
from Products.ZenReports.AliasPlugin import AliasPlugin, Column, \
                                            RRDColumnHandler, PythonColumnHandler

class filesystems( AliasPlugin ):
    "The file systems report"

    def getColumns(self):
        ##      alias/dp id : column name
        return [ Column( 'deviceName', PythonColumnHandler( 'device.titleOrId()' ) ),
                 Column('device_url', PythonColumnHandler( 'device.getDeviceUrl()' )),
                 Column( 'mount', PythonColumnHandler( 'component.mount' ) ),
                 Column( 'usedBytes', RRDColumnHandler( 'usedFilesystemSpace__bytes' ) ),
                 Column( 'totalBytes', PythonColumnHandler( 'component.totalBytes()' ) ) ]

    def getCompositeColumns(self):
        return [ Column( 'availableBytes', PythonColumnHandler('totalBytes - usedBytes if totalBytes is not None and usedBytes is not None else 0') ),
                 Column( 'percentFull', PythonColumnHandler( 'totalBytes and ' +
                        '( 100 - float(availableBytes) * 100 / float(totalBytes) )' +
                        ' or None' ) ) ]

    def getComponentPath(self):
        return 'os/filesystems'
