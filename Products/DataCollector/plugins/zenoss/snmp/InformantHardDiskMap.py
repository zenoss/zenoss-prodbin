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

__doc__ = """InformantHardDiskMap

Map SNMP Informat sub-agent to HardDisk
"""

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap

class InformantHardDiskMap(SnmpPlugin):
    """Map SNMP Informat sub-agent to HardDisk"""

    maptype = "HardDiskMap"
    modname = "Products.ZenModel.HardDisk"
    relname = "harddisks"
    compname = "hw"
    weight = 3

    snmpGetTableMaps = (
        GetTableMap('logicalDiskEntry', 
                    '.1.3.6.1.4.1.9600.1.1.1.1',
                    {
                    '.1': 'id',
                     }
        ),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        dtable = tabledata.get("logicalDiskEntry")
        if not dtable: return
        rm = self.relMap()
        for oid, disk in dtable.items():
            om = self.objectMap(disk)
            if not om.id: continue
            if om.id == "_Total": continue
            om.description = om.id
            om.id = self.prepId(om.id)
            om.snmpindex = oid.lstrip('.')
            rm.append(om)
        return rm
