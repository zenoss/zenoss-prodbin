#################################################################
#
#   Copyright (c) 2006 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from CollectorPlugin import SnmpPlugin, GetTableMap

class DellPCIMap(SnmpPlugin):
    """Map HP/Compaq insight manager PCI table to model."""

    maptype = "DellPCIMap"
    modname = "Products.ZenModel.ExpansionCard"
    relname = "cards"
    compname = "hw"

    snmpGetTableMaps = (
        GetTableMap('pciTable', 
            '.1.3.6.1.4.1.674.10892.1.1100.80.1',
            {'.6': 'slot','.8': '_manuf','.9': '_model',}
        ),
    )

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing dell pci cards for device %s' % device.id)
        getdata, tabledata = results
        pcitable = tabledata.get("pciTable")
        if not pcitable: return
        rm = self.relMap()
        for card in pcitable.values():
            om = self.objectMap(card)
            om.id = self.prepId("%s" % om.slot)
            om.setProductKey = "%s %s" % (om._manuf, om._model)
            rm.append(om)
        return rm
