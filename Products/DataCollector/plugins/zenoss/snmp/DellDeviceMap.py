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

from CollectorPlugin import SnmpPlugin, GetMap

class DellDeviceMap(SnmpPlugin):
    """Map mib elements from Dell Open Manage mib to get hw and os products.
    """

    maptype = "DellDeviceMap" 

    snmpGetMap = GetMap({ 
        #'.1.3.6.1.4.1.674.10892.1.300.10.1.8' : 'manufacturer',
        '.1.3.6.1.4.1.674.10892.1.300.10.1.9.1' : 'setHWProductKey',
        '.1.3.6.1.4.1.674.10892.1.300.10.1.11.1' : 'setHWSerialNumber',
        '.1.3.6.1.4.1.674.10892.1.400.10.1.6.1': 'setOSProductKey',
         })


    def condition(self, device, log):
        """does device meet the proper conditions for this collector to run"""
        return device.snmpOid.startswith('.1.3.6.1.4.1.674.10892.1.300.10')  
    
    
    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        return om
