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

__doc__ = """SysedgeDiskMap

Empire SysEDGE disk information.

"""

import re

from Products.DataCollector.plugins.CollectorPlugin import SnmpPlugin

class SysedgeDiskMap(SnmpPlugin):

    remoteClass = "Products.ZenModel.HardDisk"
    relationshipName = "harddisks"
    componentName = "hw"
    deviceProperties = \
                SnmpPlugin.deviceProperties + ('zSysedgeDiskMapIgnoreNames',)

    hrDeviceDescr = ".1.3.6.1.2.1.25.3.2.1.3"
    diskStatsTable = ".1.3.6.1.4.1.546.12.1.1"
    diskMap = {
        '.1':'snmpindex',
        '.9':'hostresindex',
        }


    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return False


    def collect(self, device, snmpsess, log):
        """collect snmp information from this device"""
        log.info('Collecting disks for device %s' % device.id)
        disktable = snmpsess.collectSnmpTableMap(self.diskStatsTable, 
                                                self.diskMap)
        datamaps = []
        for diskrow in disktable.values():
            descoid = self.hrDeviceDescr + '.' + str(diskrow['hostresindex'])
            desc = snmpsess.get(descoid)
            if len(desc) == 1:
                desc = desc.values()[0]
                diskrow['description'] = desc
                disknamereg = getattr(device, 
                                      'zSysedgeDiskMapIgnoreNames', None)
                if disknamereg and re.search(disknamereg, desc): continue
                id = re.split('[,\s]', desc)[0]
                diskrow['title'] = id
                diskrow['id'] = self.prepId(id)
                datamaps.append(diskrow)
        return datamaps
