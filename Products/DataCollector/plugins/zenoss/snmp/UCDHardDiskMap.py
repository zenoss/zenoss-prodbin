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

from CollectorPlugin import SnmpPlugin, GetTableMap
import re

class UCDHardDiskMap(SnmpPlugin):
    """Map UCD-DISKIO-MIB to HardDisk"""

    maptype = "HardDiskMap"
    modname = "Products.ZenModel.HardDisk"
    relname = "harddisks"
    compname = "hw"
    deviceProperties = \
        SnmpPlugin.deviceProperties + ('zHardDiskMapMatch',)

    snmpGetTableMaps = (
        GetTableMap('diskIOTable', '.1.3.6.1.4.1.2021.13.15.1.1', {
            '.2': 'id',
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
            om.description = om.id
            om.id = self.prepId(om.id)
            om.snmpindex = oid
            rm.append(om)
        return rm
