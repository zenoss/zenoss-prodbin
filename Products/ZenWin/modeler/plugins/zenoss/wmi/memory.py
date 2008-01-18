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

from Products.ZenWin.WMIPlugin import WMIPlugin

class memory(WMIPlugin):

    maptype = "FileSystemMap" 
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"


    def queryStrings(self):
        return (
            "Select TotalPhysicalMemory From Win32_ComputerSystem",
            "Select L2CacheSize From Win32_Processor",
        )
        
    def process(self, device, results, log):
        log.info('Collecting memory for device %s' % device.id)

        rm = self.relMap()
        maps = []

        for record in results[0]:
            totalMemory = int(record.TotalPhysicalMemory)
            maps.append(self.objectMap({"totalMemory": totalMemory}, compname="hw"))
        for record in results[1]:
            size = int(record.L2CacheSize)
            maps.append(self.objectMap({"totalSwap": size}, compname="os"))
        return maps