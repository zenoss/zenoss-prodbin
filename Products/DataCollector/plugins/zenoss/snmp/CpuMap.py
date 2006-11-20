#################################################################
#
#   Copyright (c) 2006 Zenoss Corporation. All rights reserved.
#
#################################################################

__doc__="""CpuMap

CpuMap maps SNMP cpu information onto CPUs

$Id: $"""

__version__ = '$Revision: 1.1 $'[11:-2]

import re

import re

from CollectorPlugin import SnmpPlugin, GetTableMap
from DataMaps import ObjectMap

class CpuMap(SnmpPlugin):

    maptype = "CPUMap"
    compname = "hw"
    relname = "cpus"
    modname = "Products.ZenModel.CPU"

    snmpGetTableMaps = (
        GetTableMap('deviceTableOid', '.1.3.6.1.2.1.25.3.2.1',
            {
             '.2': '_type',
             '.3': 'description',
             }
        ),
    )

    hrDeviceProcessor = ".1.3.6.1.2.1.25.3.1.3"

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing processor resources %s' % device.id)
        getdata, tabledata = results
        table = tabledata.get("deviceTableOid")
        maps = []
        rm = self.relMap()
        slot = 0
        for row in table.values():
            if row['_type'] != self.hrDeviceProcessor: continue
            desc = row['description']
            # try and find the cpu speed from the description
            match = re.search('([.0-9]+) *([mg]hz)', desc.lower())
            if match:
                try:
                    speed = float(match.group(1))
                    if match.group(2).startswith('g'):
                        speed *= 1000
                    row['clockspeed'] = int(speed)
                except ValueError:
                    pass
            om = self.objectMap(row)
            om.setProductKey = desc
            om.id = '%d' % slot
            slot += 1
            rm.append(om)
        maps.append(rm)
        return maps
