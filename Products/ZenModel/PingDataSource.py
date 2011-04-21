###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """PingDataSource.py

Defines datasource for zenping
"""

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo, Permissions
import Products.ZenModel.RRDDataSource as RRDDataSource


class PingDataSource(RRDDataSource.RRDDataSource):
    
    PING = 'PING'
    
    sourcetypes = (PING,)
    sourcetype = PING

    timeout = 60
    eventClass = '/Status/Ping'
        
    cycleTime = 300
    sampleSize = 1
    attempts = 2

    _properties = RRDDataSource.RRDDataSource._properties + (
        {'id':'cycleTime', 'type':'int', 'mode':'w'},
        {'id':'sampleSize', 'type':'int', 'mode':'w'},
        {'id':'attempts', 'type':'int', 'mode':'w'},
        )
        
    security = ClassSecurityInfo()

    def __init__(self, id, title=None, buildRelations=True):
        RRDDataSource.RRDDataSource.__init__(self, id, title, buildRelations)

    def getDescription(self):
        if self.sourcetype == self.PING:
            return "Ping "
        return RRDDataSource.RRDDataSource.getDescription(self)

    def useZenCommand(self):
        return False

    def addDataPoints(self):
        if not self.datapoints._getOb('rtt', None):
            self.manage_addRRDDataPoint('rtt')

    def zmanage_editProperties(self, REQUEST=None):
        '''validation, etc'''
        if REQUEST:
            # ensure default datapoint didn't go away
            self.addDataPoints()
            # and eventClass
            if not REQUEST.form.get('eventClass', None):
                REQUEST.form['eventClass'] = self.__class__.eventClass
        return RRDDataSource.RRDDataSource.zmanage_editProperties(self, REQUEST)

InitializeClass(PingDataSource)

