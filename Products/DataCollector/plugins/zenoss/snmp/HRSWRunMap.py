#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""FileSystemMap

FileSystemMap maps the interface and ip tables to interface objects

$Id: HRFileSystemMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

import re

from CollectorPlugin import SnmpPlugin, GetTableMap
from DataMaps import ObjectMap

class HRSWRunMap(SnmpPlugin):

    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"

    snmpGetTableMaps = (
        GetTableMap('hrSWRunEntry', '.1.3.6.1.2.1.25.4.2.1',
            {
             '.1': 'snmpindex',
             '.2': 'procName',
             '.5': 'parameters',
             }
        ),
    )


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing host resources storage device %s' % device.id)
        getdata, tabledata = results
        fstable = tabledata.get("hrSWRunEntry")
        filters = device.getDmdRoot("Processes").getProcFilters()
        rm = self.relMap()
        for proc in fstable.values():
            om = self.objectMap(proc)
            fullname = om.procName + " " + om.parameters
            for f in filters:
                if f(fullname):
                    break
            else:
                continue
            om.id = self.prepId(fullname)
            om.setOSProcessClass = om.procName + om.parameters
            rm.append(om)
        return rm


