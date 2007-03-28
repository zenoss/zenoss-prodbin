#################################################################
#
#   Copyright (c) 2007 Zenoss Corporation. All rights reserved.
#
#################################################################

import re

from CollectorPlugin import CommandPlugin
from DataMaps import ObjectMap


class memory(CommandPlugin):
    """
    maps vm_stat output to the memory fields
    """
    maptype = "FileSystemMap" 
    command = '/usr/sbin/sysctl hw.physmem'
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"


    def condition(self, device, log):
        return device.os.uname in ['Darwin', '']


    def process(self, device, results, log):
        log.info('Collecting memory for device %s' % device.id)

        rm = self.relMap()
        maps = []

        results = results.split(':')[1].strip()
        totalMemory = int(results)
        maps.append(ObjectMap({"totalMemory": totalMemory}, compname="hw"))
                
        return maps
