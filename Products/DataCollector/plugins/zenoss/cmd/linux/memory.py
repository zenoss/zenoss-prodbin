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

import re

from CollectorPlugin import CommandPlugin
from DataMaps import ObjectMap

MULTIPLIER = {
    'kB' : 1024,
    'MB' : 1024 * 1024,
    'b' : 1
}


class memory(CommandPlugin):
    """
    maps /proc/meminfo to the memory and swap fields
    """
    maptype = "FileSystemMap" 
    command = 'cat /proc/meminfo'
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"


    def condition(self, device, log):
        return device.os.uname == 'Linux'


    def process(self, device, results, log):
        log.info('Collecting memory and swap for device %s' % device.id)

        rm = self.relMap()
        maps = []

        for line in results.split("\n"):
            vals = line.split(':')
            if len(vals) != 2:
                continue

            name, value = vals
            vals = value.split()
            if len(vals) != 2:
                continue
            
            value, unit = vals
            size = int(value) * MULTIPLIER.get(unit, 1)
                
            if name == 'MemTotal':
                maps.append(ObjectMap({"totalMemory": size}, compname="hw"))
            if name == 'SwapTotal':
                maps.append(ObjectMap({"totalSwap": size}, compname="os"))
                
        return maps
