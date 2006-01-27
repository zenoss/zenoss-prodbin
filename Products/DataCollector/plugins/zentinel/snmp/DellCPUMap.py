#################################################################
#
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from CollectorPlugin import SnmpPlugin, GetTableMap

class DellCPUMap(SnmpPlugin):
    """Map HP/Compaq insight manager cpu table to model."""

    maptype = "DellCPUMap"
    modname = "Products.ZenModel.CPU"
    relname = "cpus"
    compname = "hw"

    snmpGetTableMaps = (
        GetTableMap('cpuTable', 
                    '.1.3.6.1.4.1.674.10892.1.1100.30.1.1',
                    {
                    '.1': 'cpuidx',
                    '.2': 'socket',
                    '.8': '_manuf',
                    '.10': '_familyidx',
                    '.12': 'clockspeed',
                    '.13': 'extspeed',
                    '.14': 'voltage',
                    '.16': '_version',
                     }
        ),
 	    GetTableMap('cacheTable', 
                    '1.3.6.1.4.1.674.10892.1.1100.40.1',
                    {'.6': 'cpuidx', '.11': 'level', '.13': 'size'}
        ),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing dell cpu for device %s' % device.id)
        getdata, tabledata = results
        cputable = tabledata.get("cpuTable")
        cachetable = tabledata.get("cacheTable")
        rm = self.relMap()
        cpumap = {}
        for cpu in cputable.values():
            om = self.objectMap(cpu)
            try: cpufam = self.cpufamily[om._familyidx]
            except IndexError: cpufam = ""
            if not cpufam.startswith(om._manuf):
                cpufam = om._manuf + " " + cpufam
            om.setProductKey =  cpufam + " " + om._version
            om.id = self.prepId("%s_%s" % (om._manuf,om.socket))
            cpumap[cpu['cpuidx']] = om
            rm.append(om)
        
        for cache in cachetable.values():
            cpu = cpumap.get(cache['cpuidx'], None)
            if cpu is None: continue
            try: level = self.cacheLevel[cpu['level']]
            except IndexError: level = None
            if level == "L1": 
                cpu.cacheSizeL1 = cache['size']
            elif level == "L2":
                cpu.cacheSizeL2 = cache['size']
        return rm


    cpufamily = (
        'other', 
        'unknown',
        "8086",
        "80286",
        "80386",
        "80486",
        "8087",
        "80287",
        "80387",
        "80487",
        "Intel Pentium",
        "Pentium Pro",
        "Pentium II",
        "Pentium MMX",
        "Celeron",
        "Xeon",
        "Pentium III",
        "Pentium III Xeon",
        "Pentium III Speed Step",
        "Itanium",
        "Intel Xeon",
        "Pentium 4",
        "Intel Xeon MP",
        "Intel Itanium 2",
    )

    cacheLoc = ('other','unknown','internal','external')
    cacheLevel = ('other', 'unknown', 'L1', 'L2', 'L3')
