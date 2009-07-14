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
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.

__doc__ = """
Map UCD-DISKIO-MIB OIDs to the HardDisk relation.
"""

import re
from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin, GetTableMap

class UCDHardDiskMap(SnmpPlugin):

    maptype = "HardDiskMap"
    modname = "Products.ZenModel.HardDisk"
    relname = "harddisks"
    compname = "hw"
    deviceProperties = \
        SnmpPlugin.deviceProperties + ('zHardDiskMapMatch',)

    snmpGetTableMaps = (
        GetTableMap('diskIOTable', '.1.3.6.1.4.1.2021.13.15.1.1', {
            '.2': 'id',
            '.3': 'rdb',
            '.4': 'wtb',
            '.5': 'rdc',
            '.6': 'wtc',
            }
        ),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        dtable = tabledata.get("diskIOTable")
        if not dtable: return
        diskmatch = re.compile(
                getattr(device, 'zHardDiskMapMatch', 'WillNotEverMatch'))

        rm = self.relMap()
        for oid, disk in dtable.items():
            om = self.objectMap(disk)
            if not diskmatch.search(om.id): continue
            rdb = getattr(om, 'rdb', 0)
            wtb = getattr(om, 'wtb', 0)
            rdc = getattr(om, 'rdc', 0)
            wtc = getattr(om, 'wtc', 0)
            if rdb + wtb + rdc + wtc <= 0: continue
            om.description = om.id
            om.id = self.prepId(om.id)
            om.snmpindex = oid
            rm.append(om)
        return rm
