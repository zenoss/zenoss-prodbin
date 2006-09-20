#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

__doc__="""FileSystemMap

FileSystemMap maps the interface and ip tables to interface objects

$Id: HRSWInstalledMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

import struct

from CollectorPlugin import SnmpPlugin, GetTableMap

class HRSWInstalledMap(SnmpPlugin):

    maptype = "SoftwareMap"
    modname = "Products.ZenModel.Software"
    relname = "software"
    compname = "os"

    snmpGetTableMaps = (
        GetTableMap('swTableOid', '.1.3.6.1.2.1.25.6.3.1',
                {'.1': 'snmpindex',
                 '.2': 'setProductKey',
                 #'.4': 'type',
                 '.5': 'setInstallDate',
                 }
        ),
    )


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing host resources software for device %s' % device.id)
        getdata, tabledata = results
        swtable = tabledata.get("swTableOid")
        rm = self.relMap()
        for sw in swtable.values():
            om = self.objectMap(sw)
            om.id = self.prepId(om.setProductKey)
            if hasattr(om, 'setInstallDate'):
                om.setInstallDate = self.asdate(om.setInstallDate)
            rm.append(om)
        return rm
