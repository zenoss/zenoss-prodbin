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

__doc__ = """DeviceMap

DeviceMap maps the interface and ip tables to interface objects

"""

import re
import sys

from Products.DataCollector.plugins.CollectorPlugin \
    import SnmpPlugin, GetMap, GetTableMap

class DeviceMap(SnmpPlugin):

    maptype = "DeviceMap" 

    columns = {
             '.1.3.6.1.2.1.1.1.0' : 'snmpDescr',
             '.1.3.6.1.2.1.1.2.0' : 'snmpOid',
             #'.1.3.6.1.2.1.1.3.0' : 'snmpUpTime',
             '.1.3.6.1.2.1.1.4.0' : 'snmpContact',
             '.1.3.6.1.2.1.1.5.0' : 'snmpSysName',
             '.1.3.6.1.2.1.1.6.0' : 'snmpLocation',
             }
    snmpGetMap = GetMap(columns)

    snmpGetTableMaps = (
        GetTableMap('entPhysicalTable', '.1.3.6.1.2.1.47.1.1.1.1', {
            '.11': 'serialNum'
            }),
        )

    ciscoVersion = re.compile(r'Version (?P<ver>.+), ')
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        if not self.checkColumns(getdata, self.columns, log): 
            return 
        om = self.objectMap(getdata)

        # allow for custom parse of DeviceMap data
        scDeviceMapParse = getattr(device, 'scDeviceMapParse', None)
        if scDeviceMapParse:
            om = scDeviceMapParse(device, om)

        # Find device serial number using the first entry in ENTITY-MIB.
        entPhysicalTable = tabledata.get('entPhysicalTable', {})

        lowestIndex = sys.maxint
        for index, entry in entPhysicalTable.items():
            serialNum = entry.get('serialNum', None)
            if serialNum and int(index) > lowestIndex:
                om.setHWSerialNumber = serialNum
                lowestIndex = int(index)

        return om
