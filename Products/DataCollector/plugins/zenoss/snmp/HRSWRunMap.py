###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__="""HRSWRunMap

HRSWRunMap maps the processes running on the system to OSProcess objects.
Uses the HOST-RESOURCES-MIB OIDs.

"""

from Products.DataCollector.plugins.CollectorPlugin \
    import SnmpPlugin, GetTableMap

HRSWRUNENTRY = '.1.3.6.1.2.1.25.4.2.1'

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
        GetTableMap('hrSWRunEntry', HRSWRUNENTRY, columns),
    )

    def process(self, device, results, log):
        """
        Process the SNMP information returned from a device
        """
        log.info('Processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        log.debug("%s tabledata = %s", device.id, tabledata)
        
        #get the SNMP process data
        pidtable = tabledata.get("hrSWRunEntry")
        if pidtable is None:
            log.error("Unable to get data for %s from hrSWRunEntry %s"
                          " -- skipping model", HRSWRUNENTRY, device.id)
            return None
        
        log.debug("=== Process information received ===")
        for p in sorted(pidtable.keys()):
            log.debug("snmpidx: %s\tprocess: %s" % (p, pidtable[p]))
        
        rm = self.relMap()
        for proc in pidtable.values():
            om = self.objectMap(proc)
            ppath = getattr(om, '_procPath', False) 
            if ppath and ppath.find('\\') == -1:
                om.procName = om._procPath
            if not getattr(om, 'procName', False): 
                log.warn("Skipping process with no name")
                continue
            om.parameters = getattr(om, 'parameters', '')
            rm.append(om)

        if not rm:
            log.warning("No process information from hrSWRunEntry %s",
                        HRSWRUNENTRY)
            return None

        return rm

