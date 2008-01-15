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

class process(CommandPlugin):
    """
    maps ps output to process
    """
    maptype = "OSProcessMap" 
    command = 'ps axho comm,args'
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    classname = "createFromObjectMap"


    def condition(self, device, log):
        return device.os.uname == 'Linux'


    def process(self, device, results, log):
        log.info('Collecting process information for device %s' % device.id)

        rm = self.relMap()

        for line in results.split("\n"):
            vals = line.split()
            if len(vals) == 0:
                continue

            procName = vals[0]
            parameters = string.join(vals[1:], ' ')
            
            proc = dict(procName=procName, parameters=parameters)
            om = self.objectMap(proc)
            rm.append(om)

        return rm
