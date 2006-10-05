#################################################################
#
#   Copyright (c) 2006 Zenoss. All rights reserved.
#
#################################################################

from CollectorPlugin import CommandPlugin

class uname(CommandPlugin):
    
    maptype = "DeviceMap" 
    compname = "os"
    command = 'uname'

    def process(self, device, results, log):
        """collect snmp information from this device"""
        log.info('processing os uname info for device %s' % device.id)
        om = self.objectMap()
        om.uname = results.strip()
        return om
