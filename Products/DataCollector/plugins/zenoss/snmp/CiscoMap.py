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

import re
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

    badSerialPatterns = [
        # Cisco, Catalyst, CAT
        r'^(Cisco|Catalyst|CAT)$',

        # 0x0E
        r'^0x',

        # WS-C3548-XL
        r'^WS-',

        # VG224
        r'^VG\d{3}$',

        # C3845-VSEC-SRST/K9
        r'^C\d{4}-',

        # Model numbers: 1841, 2811, 2851, 3845, etc.
        r'^\d{4}$',

        # Other
        r'^(CISCO|C|Cat|CAT)?\d{4}[A-Z](-\d{0,3})?$',
        ]


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)

        # In most cases we want to prefer the serial number in the Cisco
        # enterprise MIB if it is available.
        if getattr(om, 'setHWSerialNumber', False):

            # If there's a space in the serial we only want the first part.
            om.setHWSerialNumber = om.setHWSerialNumber.split(' ', 1)[0]

            # Some Cisco devices return a bogus serial. Ignore them.
            for pattern in self.badSerialPatterns:
                if re.match(pattern, om.setHWSerialNumber):
                    break
            else:
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
        if getattr(om, 'setHWSerialNumber', False):
            return om
        else:
            return None

