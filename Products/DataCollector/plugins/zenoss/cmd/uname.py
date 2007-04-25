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


