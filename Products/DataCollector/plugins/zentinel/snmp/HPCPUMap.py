#################################################################
#
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from CollectorPlugin import SnmpPlugin, GetTableMap

class HPCPUMap(SnmpPlugin):
    """Map HP/Compaq insight manager cpu table to model."""

    maptype = "HPCPUMap"
    modname = "Products.ZenModel.CPU"
    relname = "cpus"
    compname = "hw"

    snmpGetTableMaps = (
        GetTableMap('cpuTable', '.1.3.6.1.4.1.232.1.2.2.1.1',
                {
                '.1': '_cpuidx',
                '.3': 'setProductKey',
                '.4': 'clockspeed',
                '.7': 'extspeed',
                '.9': 'socket',
                 }
        ),
 	    GetTableMap('cacheTable', '1.3.6.1.4.1.232.1.2.2.3.1',
                {'.1': '_cpuidx', '.2': 'level', '.3': 'size'}
        ),
    )


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing hp cpu info for device %s' % device.id)
        getdata, tabledata = results
        cputable = tabledata.get("cpuTable")
        cachetable = tabledata.get("cacheTable")
        rm = self.relMap()
        cpumap = {}
        for cpu in cputable.values():
            om = self.objectMap(cpu)
            om.id = self.prepId("%s_%s" % (om.setProductKey,om.socket))
            cpumap[cpu['_cpuidx']] = om
            rm.append(om)
        
        for cache in cachetable.values():
            cpu = cpumap.get(cache['cpuidx'], None)
            if cpu is None: continue
            if cache['level'] == 1: 
                cpu.cacheSizeL1 = cache['size']
            elif cache['level'] == 2:
                cpu.cacheSizeL2 = cache['size']
        return rm
