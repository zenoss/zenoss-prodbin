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

__doc__="""FileSystemMap

FileSystemMap maps the interface and ip tables to interface objects

$Id: HRFileSystemMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin, GetTableMap
from DataMaps import ObjectMap

class HRFileSystemMap(SnmpPlugin):

    maptype = "FileSystemMap"
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"

    columns = {
         '.1': 'snmpindex',
         '.2': 'type',
         '.3': 'mount',
         '.4': 'blockSize',
         '.5': 'totalBlocks',
         }

    snmpGetTableMaps = (
        GetTableMap('fsTableOid', '.1.3.6.1.2.1.25.2.3.1', columns),
    )

    typemap = { 
        ".1.3.6.1.2.1.25.2.1.2": "ram",
        ".1.3.6.1.2.1.25.2.1.3": "swap",
        ".1.3.6.1.2.1.25.2.1.4": "fixedDisk",
        }


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        fstable = tabledata.get("fsTableOid")
        skipfsnames = getattr(device, 'zFileSystemMapIgnoreNames', None)
        maps = []
        rm = self.relMap()
        for fs in fstable.values():
            if not fs.has_key("totalBlocks"): continue
            if not self.checkColumns(fs, self.columns, log): continue
            fstype = self.typemap.get(fs['type'],None)
            size = long(fs['blockSize'] * fs['totalBlocks'])
            if fstype == "ram":
                maps.append(ObjectMap({"totalMemory": size}, compname="hw"))
            elif fstype == "swap":
                maps.append(ObjectMap({"totalSwap": size}, compname="os"))
            elif (fstype == "fixedDisk" and size > 0 and 
                (not skipfsnames or not re.search(skipfsnames,fs['mount']))):
                om = self.objectMap(fs)
                om.id = self.prepId(om.mount)
                rm.append(om)
        maps.append(rm)
        return maps


