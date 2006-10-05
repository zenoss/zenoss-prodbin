#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

import re

from CollectorPlugin import CommandPlugin

class dfB1(CommandPlugin):
    """
    ifconfig maps a linux ifconfig command to the interfaces relation.
    """
    maptype = "FilesystemMap" 
    command = '/bin/df -B1k'
    compname = "os"
    relname = "filesystems"
    modname = "Products.ZenModel.FileSystem"


    def condition(self, device, log):
        return device.os.uname == 'Linux'


    def process(self, device, results, log):
        log.info('Collecting filesystems for device %s' % device.id)
        rm = self.relMap()
        rlines = results.split("\n")
        bline = ""
        for line in rlines:
            if line.startswith("Filesystem"): continue
            om = self.objectMap()
            spline = line.split()
            if len(spline) == 1:
                bline = spline[0]
                continue
            if bline: 
                spline.insert(0,bline)
                bline = None
            if len(spline) != 6: continue
            (om.storageDevice, tblocks, u, a, p, om.mount) = spline
            om.totalBlocks = long(tblocks)
            om.blockSize = 1024
            om.id = self.prepId(om.mount)
            rm.append(om)
        return rm
