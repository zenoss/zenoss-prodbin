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
from sets import Set
import md5

class HRSWRunMap(SnmpPlugin):

    maptype = "OSProcessMap"
    compname = "os"
    relname = "processes"
    modname = "Products.ZenModel.OSProcess"

    snmpGetTableMaps = (
        GetTableMap('hrSWRunEntry', '.1.3.6.1.2.1.25.4.2.1',
            {
             '.1': 'snmpindex',
             '.4': 'procName',
             '.5': 'parameters',
             }
        ),
    )


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing host resources storage device %s' % device.id)
        getdata, tabledata = results
        fstable = tabledata.get("hrSWRunEntry")
        rm = self.relMap()
        procs = Set()
        for proc in fstable.values():
            om = self.objectMap(proc)
            if not hasattr(om, 'procName') or om.procName == "": 
                log.warn("Your hrSWRun table is broken, "
                        " zenoss can't do process monitoring")
                return rm

            fullname = (om.procName + " " + om.parameters).rstrip()

            processes = device.getDmdRoot("Processes")
            for pc in processes.getSubOSProcessClassesGen():
                if pc.match(fullname):
                    om.setOSProcessClass = pc.getPrimaryDmdId()
                    id = om.procName
                    parameters = om.parameters.strip()
                    if parameters and not pc.ignoreParameters:
                        parameters = md5.md5(parameters).hexdigest()
                        id += ' ' + parameters
                    om.id = self.prepId(id)
                    if id not in procs:
                        procs.add(id)
                        rm.append(om)
                    break
            
        return rm


