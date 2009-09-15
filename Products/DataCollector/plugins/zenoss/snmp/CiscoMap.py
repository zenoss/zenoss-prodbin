###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """CiscoMap

CiscoMap maps cisco serialnumber information 

"""

import sys
from Products.DataCollector.plugins.CollectorPlugin \
    import SnmpPlugin, GetMap, GetTableMap

class CiscoMap(SnmpPlugin):

    maptype = "CiscoDeviceMap"

    snmpGetMap = GetMap({
             '.1.3.6.1.4.1.9.3.6.3.0' : 'setHWSerialNumber',
             })

    snmpGetTableMaps = (
        GetTableMap('entPhysicalTable', '.1.3.6.1.2.1.47.1.1.1.1', {
            '.11': 'serialNum'
            }),
        )


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)

        # In most cases we want to prefer the serial number in the Cisco
        # enterprise MIB if it is available.
        if om.setHWSerialNumber \
            and ' ' not in om.setHWSerialNumber \
            and not om.setHWSerialNumber.startswith('0x'):
            return om

        # Some Cisco devices expose their serial number via the ENTITY-MIB.
        entPhysicalTable = tabledata.get('entPhysicalTable', {})

        lowestIndex = sys.maxint
        for index, entry in entPhysicalTable.items():
            serialNum = entry.get('serialNum', None)
            if serialNum and int(index) < lowestIndex:
                om.setHWSerialNumber = serialNum
                lowestIndex = int(index)

        # Return the serial number if we found one. Otherwise don't overwrite
        # a value provided by another modeler plugin.
        if om.setHWSerialNumber:
            return om
        else:
            return None
