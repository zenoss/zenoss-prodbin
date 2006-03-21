#################################################################
#
#   Copyright (c) 2006 Confmon Corporation. All rights reserved.
#
#################################################################

from CollectorPlugin import SnmpPlugin, GetMap

class PowerwareDeviceMap(SnmpPlugin):
    """Map mib elements from Dell Open Manage mib to get hw and os products.
    """

    maptype = "PowerwareDeviceMap" 

    snmpGetMap = GetMap({ 
        '.1.3.6.1.4.1.534.1.1.2.0': 'setHWProductKey',
         })


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing Powerware device info on device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        return om
