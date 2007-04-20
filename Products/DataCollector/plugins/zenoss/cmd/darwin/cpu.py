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

__doc__="""CpuMap

Uses sysctl to map cpu information on CPU objects

$Id: $"""

__version__ = '$Revision: 1.1 $'[11:-2]

import re

from CollectorPlugin import CommandPlugin, GetTableMap
from DataMaps import ObjectMap

class cpu(CommandPlugin):

    maptype = "CPUMap"
    compname = "hw"
    relname = "cpus"
    modname = "Products.ZenModel.CPU"
    command = '/usr/sbin/sysctl -a'

    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return device.os.uname == 'Darwin' 


    def process(self, device, results, log):
        """parse command output from this device"""
        log.info('processing processor resources %s' % device.id)
        maps = []
        rm = self.relMap()
        
        config = {}
        for row in results.split('\n'):
            if len(row.strip()) == 0: continue

            values = row.split(':')
            if len(values) < 2: continue
            name, value = values[0:2]

            name = name.strip()
            value = value.strip()

            if name == 'hw.cpufrequency': config['clockspeed'] = int(value)
            if name == 'hw.l1icachesize': config['cacheSizeL1'] = int(value) / 1024
            if name == 'hw.l2cachesize': config['cacheSizeL2'] = int(value) / 1024
            if name == 'machdep.cpu.brand_string': config['description'] = value
                
        om = self.objectMap(config)
        om.setProductKey = config['description']
        om.id = '0'
        rm.append(om)
        maps.append(rm)
        return maps
