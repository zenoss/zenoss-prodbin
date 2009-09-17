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
from Products.ZenReports.AliasPlugin import AliasPlugin, Column, \
                                            PythonColumnHandler, \
                                            RRDColumnHandler

def _getAvailableReal( availableBytes, bufferedBytes, cachedBytes ):
    if availableBytes is None:
        return None
    elif bufferedBytes is None or cachedBytes is None:
        return availableBytes
    else:
        return availableBytes + bufferedBytes + cachedBytes

def _getPercentUtilization( availableReal, totalReal ):
    if totalReal and availableReal:
        return Utils.percent( totalReal - availableReal, totalReal )
    else:
        return None

class memory( AliasPlugin ):
    "The memory usage report"

    def getColumns(self):
        return [
                Column('deviceName', PythonColumnHandler( 'device.titleOrId()' )),
                Column('totalReal', PythonColumnHandler( 'device.hw.totalMemory')),
                Column('availableReal_tmp', RRDColumnHandler( 'memoryAvailable__bytes')),
                Column('buffered', RRDColumnHandler('memoryBuffered__bytes')),
                Column('cached', RRDColumnHandler('memoryCached__bytes')) ]

    def getCompositeColumns(self):
        return [Column('availableReal',
                        PythonColumnHandler(
                            'getAvailableReal( availableReal_tmp, buffered, cached )',
                            dict( getAvailableReal=_getAvailableReal ) ) ),
                Column('percentUsed',
                        PythonColumnHandler(
                            'getPercentUtilization(availableReal,totalReal)',
                            dict( getPercentUtilization=_getPercentUtilization))) ]
