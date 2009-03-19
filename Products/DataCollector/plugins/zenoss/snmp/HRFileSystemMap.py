###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """FileSystemMap

FileSystemMap maps the filesystems to filesystem objects

"""

import re

from Products.ZenUtils.Utils import unsigned
from Products.DataCollector.plugins.DataMaps import ObjectMap
from Products.DataCollector.plugins.CollectorPlugin \
    import SnmpPlugin, GetTableMap

class HRFileSystemMap(SnmpPlugin):

    maptype = "FileSystemMap"
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"
    deviceProperties = SnmpPlugin.deviceProperties + (
      'zFileSystemMapIgnoreNames', 'zFileSystemMapIgnoreTypes')

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
        ".1.3.6.1.2.1.25.2.1.1": "other",
        ".1.3.6.1.2.1.25.2.1.2": "ram",
        ".1.3.6.1.2.1.25.2.1.3": "virtualMemory",
        ".1.3.6.1.2.1.25.2.1.4": "fixedDisk",
        ".1.3.6.1.2.1.25.2.1.5": "removableDisk",
        ".1.3.6.1.2.1.25.2.1.6": "floppyDisk",
        ".1.3.6.1.2.1.25.2.1.7": "compactDisk",
        ".1.3.6.1.2.1.25.2.1.8": "ramDisk",
        ".1.3.6.1.2.1.25.2.1.9": "flashMemory",
        ".1.3.6.1.2.1.25.2.1.10": "networkDisk",
        }


    def process(self, device, results, log):
        """Process SNMP information from this device"""
        log.info('Modeler %s processing data for device %s', self.name(), device.id)
        getdata, tabledata = results
        log.debug("%s tabledata = %s", device.id, tabledata)
        fstable = tabledata.get("fsTableOid")
        if fstable is None:
            log.error("Unable to get data for %s from fsTableOid"
                          " -- skipping model" % device.id)
            return None

        skipfsnames = getattr(device, 'zFileSystemMapIgnoreNames', None)
        skipfstypes = getattr(device, 'zFileSystemMapIgnoreTypes', None)
        maps = []
        rm = self.relMap()
        for fs in fstable.values():
            if not self.checkColumns(fs, self.columns, log):
                continue
            
            # Gentoo and openSUSE report "Virtual memory" as swap. This needs
            # to be ignored so we can pickup the real swap later in the table.
            if fs['mount'].lower() == "virtual memory":
                continue

            totalBlocks = fs['totalBlocks']

            # This may now be a redundant check. Candidate for removal.
            #   http://dev.zenoss.org/trac/ticket/4556
            if totalBlocks < 0:
                fs['totalBlocks'] = unsigned(totalBlocks)

            size = long(fs['blockSize'] * totalBlocks)
            if size <= 0:
                log.info("Skipping %s. 0 total blocks.", fs['mount'])
                continue
            
            fs['type'] = self.typemap.get(fs['type'], "other")
            size = long(fs['blockSize'] * totalBlocks)
            
            # Handle file systems that need to be mapped into other parts of
            # the model such as total memory or total swap.
            if fs['type'] == "ram":
                maps.append(ObjectMap({"totalMemory": size}, compname="hw"))
            elif fs['type'] == "virtualMemory":
                maps.append(ObjectMap({"totalSwap": size}, compname="os"))
            
            if skipfsnames and re.search(skipfsnames, fs['mount']):
                log.info("Skipping %s as it matches zFileSystemMapIgnoreNames.",
                    fs['mount'])
                continue
            
            if skipfstypes and fs['type'] in skipfstypes:
                log.info("Skipping %s (%s) as it matches zFileSystemMapIgnoreTypes.",
                    fs['mount'], fs['type'])
                continue

            om = self.objectMap(fs)
            om.id = self.prepId(om.mount)
            rm.append(om)
        maps.append(rm)
        return maps


