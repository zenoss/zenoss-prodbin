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
        return device.os.uname == 'Darwin' 


    def process(self, device, results, log):
        log.info('Collecting memory for device %s' % device.id)

        rm = self.relMap()
        maps = []

        results = results.split(':')[1].strip()
        totalMemory = int(results)
        maps.append(ObjectMap({"totalMemory": totalMemory}, compname="hw"))
                
        return maps
