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

import string

from CollectorPlugin import CommandPlugin
from sets import Set
import md5


class process(CommandPlugin):
    """
    maps ps output to process
    """
    maptype = "OSProcessMap" 
    command = '/bin/ps axho command'
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    classname = "createFromObjectMap"


    def condition(self, device, log):
        return device.os.uname == 'Darwin' 


    def process(self, device, results, log):
        log.info('Collecting process information for device %s' % device.id)

        rm = self.relMap()
        for line in results.split("\n")[1:]:
            vals = line.split(None, 1)
            if len(vals) != 2: continue
            proc = dict(procName=vals[0], parameters=vals[1])
            om = self.objectMap(proc)
            rm.append(om)
        return rm
