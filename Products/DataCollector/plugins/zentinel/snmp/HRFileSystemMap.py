#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

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

    snmpGetTableMaps = (
        GetTableMap('fsTableOid', '.1.3.6.1.2.1.25.2.3.1',
            {
             '.1': 'snmpindex',
             '.2': 'type',
             '.3': 'mount',
             '.4': 'blockSize',
             '.5': 'totalBlocks',
             '.6': 'usedBlocks',
             }
        ),
    )

    typemap = { 
        ".1.3.6.1.2.1.25.2.1.2": "ram",
        ".1.3.6.1.2.1.25.2.1.3": "swap",
        ".1.3.6.1.2.1.25.2.1.4": "fixedDisk",
        }


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing host resources storage device %s' % device.id)
        getdata, tabledata = results
        fstable = tabledata.get("fsTableOid")
        skipfsnames = getattr(device, 'zFileSystemMapIgnoreNames', None)
        maps = []
        rm = self.relMap()
        for fs in fstable.values():
            fstype = self.typemap.get(fs['type'],None)
            if not fs.has_key("totalBlocks"): continue
            size = long(fs['blockSize'] * fs['totalBlocks'])
            if fstype == "ram":
                maps.append(ObjectMap({"totalMemory": size}, compname="hw"))
            elif fstype == "swap":
                maps.append(ObjectMap({"totalSwap": size}, compname="os"))
            elif (fstype == "fixedDisk" and size > 0 and 
                (not skipfsnames or not re.search(skipfsnames,fs['mount']))):
                om = self.objectMap(fs)
                om.id = self.prepId(om.mount)
                om.totalBytes = size
                om.blockSize = long(om.blockSize)
                om.availBytes = long(om.blockSize * 
                                    (om.totalBlocks - om.usedBlocks))
                om.usedBytes = long(om.blockSize * om.usedBlocks)
                om.capacity = "%d" % (om.usedBytes / float(size) * 100)
                delattr(om,'totalBlocks')
                delattr(om,'usedBlocks')
                rm.append(om)
        maps.append(rm)
        return maps


