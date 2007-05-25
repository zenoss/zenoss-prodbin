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

$Id: HRSWInstalledMap.py,v 1.2 2004/04/07 16:26:53 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

import struct

from CollectorPlugin import SnmpPlugin, GetTableMap

class HRSWInstalledMap(SnmpPlugin):

    maptype = "SoftwareMap"
    modname = "Products.ZenModel.Software"
    relname = "software"
    compname = "os"

    columns = {
        '.1': 'snmpindex',
         '.2': 'setProductKey',
         #'.4': 'type',
         '.5': 'setInstallDate',
         }
    snmpGetTableMaps = (
        GetTableMap('swTableOid', '.1.3.6.1.2.1.25.6.3.1', columns),
    )


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        swtable = tabledata.get("swTableOid")
        rm = self.relMap()
        for sw in swtable.values():
            if not rm and not self.checkColumns(sw, self.columns, log): 
                return rm
            om = self.objectMap(sw)
            om.id = self.prepId(om.setProductKey)
            if not om.id: continue
            if hasattr(om, 'setInstallDate'):
                om.setInstallDate = self.asdate(om.setInstallDate)
            rm.append(om)
        return rm
