#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""InterfaceMap

InterfaceMap maps the interface and ip tables to interface objects

$Id: SysedgeDiskMap.py,v 1.1 2003/04/16 20:57:22 edahl Exp $"""

__version__ = '$Revision: 1.1 $'[11:-2]

import re

from CustomRelMap import CustomRelMap

class SysedgeDiskMap(CustomRelMap):

    hrDeviceDescr = "1.3.6.1.2.1.25.3.2.1.3"
    diskStatsTable = "1.3.6.1.4.1.546.12.1.1"
    diskMap = {
        '.1':'snmpindex',
        '.9':'hostresindex',
        }

    prepId = re.compile(r'[^a-zA-Z0-9-_.]')


    def __init__(self):
        CustomRelMap.__init__(self, 'harddisks', 'ZenModel.HardDisk')


    def condition(self, device, snmpsess, log):
        """does device meet the proper conditions for this collector to run"""
        data = None
        try:
            data = snmpsess.get('.1.3.6.1.4.1.546.1.1.1.17.0')
        except:pass
        return data


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
                diskrow['id'] = self.prepId.sub('_', id)
                datamaps.append(diskrow)
        return datamaps
