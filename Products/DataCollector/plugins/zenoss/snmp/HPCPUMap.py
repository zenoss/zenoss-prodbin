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
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.

from CollectorPlugin import SnmpPlugin, GetTableMap

class HPCPUMap(SnmpPlugin):
    """Map HP/Compaq insight manager cpu table to model."""

    maptype = "HPCPUMap"
    modname = "Products.ZenModel.CPU"
    relname = "cpus"
    compname = "hw"

    cpucols = {
        '.1': '_cpuidx',
        '.3': 'setProductKey',
        '.4': 'clockspeed',
        '.7': 'extspeed',
        '.9': 'socket',
         }

    cachecols = {'.1': 'cpuidx', '.2': 'level', '.3': 'size'}

    snmpGetTableMaps = (
        GetTableMap('cpuTable', '.1.3.6.1.4.1.232.1.2.2.1.1', cpucols),
            GetTableMap('cacheTable', '1.3.6.1.4.1.232.1.2.2.3.1', cachecols), 
    )


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        cputable = tabledata.get("cpuTable")
        cachetable = tabledata.get("cacheTable")
        if not cputable or not cachetable: return
        rm = self.relMap()
        cpumap = {}
        for cpu in cputable.values():
            om = self.objectMap(cpu)
            idx = getattr(om, 'socket', om._cpuidx)
            om.id = self.prepId("%s_%s" % (om.setProductKey,idx))
            cpumap[cpu['_cpuidx']] = om
            rm.append(om)
        
        for cache in cachetable.values():
            cpu = cpumap.get(cache['cpuidx'], None)
            if cpu is None: continue
            if cache['level'] == 1: 
                cpu.cacheSizeL1 = cache.get('size',0)
            elif cache['level'] == 2:
                cpu.cacheSizeL2 = cache.get('size',0)
        return rm
