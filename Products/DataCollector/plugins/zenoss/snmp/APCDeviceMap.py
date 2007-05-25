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

class APCDeviceMap(SnmpPlugin):
    """Map mib elements from Dell Open Manage mib to get hw and os products.
    """

    maptype = "APCDeviceMap" 

    snmpGetMap = GetMap({ 
        '.1.3.6.1.4.1.318.1.1.1.1.1.1.0': 'setHWProductKey',
        '.1.3.6.1.4.1.318.1.1.1.1.2.3.0': 'setHWSerialNumber',
         })


    def condition(self, device, log):
        """only for boxes with proper object id
        """
        return device.snmpOid.startswith(".1.3.6.1.4.1.318")


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing %s for device %s', self.name(), device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        return om
