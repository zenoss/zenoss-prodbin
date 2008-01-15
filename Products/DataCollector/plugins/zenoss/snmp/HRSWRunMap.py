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

__doc__="""FileSystemMap

FileSystemMap maps the interface and ip tables to interface objects

$Id: HRFileSystemMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

from CollectorPlugin import SnmpPlugin, GetTableMap

class HRSWRunMap(SnmpPlugin):

    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"
    classname = 'createFromObjectMap'

    columns = {
         '.1': 'snmpindex',
         '.2': 'procName',
         '.4': '_procPath',
         '.5': 'parameters',
         }

    snmpGetTableMaps = (
        GetTableMap('hrSWRunEntry', '.1.3.6.1.2.1.25.4.2.1', columns),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        
        #get the SNMP process data
        fstable = tabledata.get("hrSWRunEntry")
        
        log.debug("=== process information received ===")
        for p in fstable.keys():
            log.debug("snmpidx: %s\tprocess: %s" % (p, fstable[p]))
        
        rm = self.relMap()
        for proc in fstable.values():
            om = self.objectMap(proc)
            ppath = getattr(om, '_procPath', False) 
            if ppath and ppath.find('\\') == -1:
                om.procName = om._procPath
            if not getattr(om, 'procName', False): 
                log.warn("Skipping process with no name")
                continue
            om.parameters = getattr(om, 'parameters', '')
            rm.append(om)
        return rm


