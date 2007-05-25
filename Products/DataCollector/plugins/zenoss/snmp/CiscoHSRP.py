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

__doc__="""InterfaceMap

InterfaceMap maps the interface and ip tables to interface objects

$Id: InterfaceMap.py,v 1.24 2003/10/30 18:42:19 edahl Exp $"""

__version__ = '$Revision: 1.24 $'[11:-2]

import transaction

from CollectorPlugin import SnmpPlugin, GetTableMap

class CiscoHSRP(SnmpPlugin):

    order = 10000
    maptype = "CiscoHSRP" 

    snmpGetTableMaps = (
        # HSRP Table
        GetTableMap('hsrpTable', '.1.3.6.1.4.1.9.9.106.1.2.1.1', 
                {
                '.11': 'vip',  # virtual ip ifindex is second to last id
                '.13': 'actip', # ip of active router
                #'.16': 'vmacaddress'
                 }
        ),
    )

    def condition(self, device, log):
        return device.hw.getManufacturerName() == "Cisco"
        
   
    def process(self, device, results, log):
        """Add HSRP addresses to an interface.  We need to do this
        Within the processing code because we aren't adding or removing
        objects from a relaiton.  Be very carefull about transaction
        boundries and check for changes before actually chaning things.
        """
        changed = False
        getdata, tabledata = results
        log.info('processing %s for device %s', self.name(), device.id)
        hsrptable = tabledata.get("hsrpTable")
        if not hsrptable: return
        nets = device.getDmdRoot("Networks")
        transaction.begin()
        for hsrp in hsrptable.values():
            actip = hsrp['actip']
            vip = hsrp['vip']
            actip = nets.findIp(actip)
            if not actip: 
                log.warn("active ip %s on device %s not found",actip,device.id)
                continue
            intr = actip.interface()
            if not intr:
                log.warn("active ip %s on device %s no interface", 
                          actip, device.id)
                continue
            intr = intr.primaryAq()
            vip = "%s/%s" % (vip, actip.netmask) 
            if vip not in intr.getIpAddresses():
                log.info("adding vip %s to device %s interface %s", 
                        vip, intr.getDeviceName(), intr.id)
                intr.addIpAddress(vip)
                changed = True
        if changed: transaction.commit()      
        else: transaction.abort()
