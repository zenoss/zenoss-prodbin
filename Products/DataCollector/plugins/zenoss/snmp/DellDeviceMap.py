#################################################################
#
#   Copyright (c) 2006 Confmon Corporation. All rights reserved.
#
#################################################################

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


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing dell device info on device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        return om
