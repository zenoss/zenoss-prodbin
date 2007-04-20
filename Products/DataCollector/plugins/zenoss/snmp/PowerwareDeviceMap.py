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

class PowerwareDeviceMap(SnmpPlugin):
    """Map mib elements from Dell Open Manage mib to get hw and os products.
    """

    maptype = "PowerwareDeviceMap" 

    snmpGetMap = GetMap({ 
        '.1.3.6.1.4.1.534.1.1.2.0': 'setHWProductKey',
         })


    def condition(self, device, log):
        """only for boxes with proper object id
        """
        return device.snmpOid.startswith(".1.3.6.1.4.1.534")


    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing Powerware device info on device %s' % device.id)
        getdata, tabledata = results
        om = self.objectMap(getdata)
        return om
