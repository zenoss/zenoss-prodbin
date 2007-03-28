#################################################################
#
#   Copyright (c) 2007 Zenoss Corporation. All rights reserved.
#
#################################################################

import re

from CollectorPlugin import CommandPlugin
from DataMaps import ObjectMap

MULTIPLIERS = {
    'M' : 1024 * 1024,
    'K' : 1024,
    'B' : 1
    }

class swap(CommandPlugin):
    """
    reads from sysctl and puts the swap total into the swap field
    """
    maptype = "FileSystemMap" 
    command = '/usr/sbin/sysctl vm.swapusage'
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"


    def condition(self, device, log):
        return device.os.uname in ['Darwin', '']


    def process(self, device, results, log):
        log.info('Collecting swap for device %s' % device.id)

        rm = self.relMap()
        maps = []

        results = results.split()
        total = results[3]
        multiplier = MULTIPLIERS[total[-1]]

        total = float(total[:-1]) * multiplier
        maps.append(ObjectMap({"totalSwap": total}, compname="os"))
                
        return maps
