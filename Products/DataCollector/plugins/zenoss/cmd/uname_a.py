###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

_doc__ = """uname -a
Determine snmpSysName and setOSProductKey from the result of the uname -a
command.
"""

from CollectorPlugin import CommandPlugin

class uname_a(CommandPlugin):
    
    maptype = "DeviceMap" 
    compname = ""
    command = 'uname -a'

    def process(self, device, results, log):
        """Collect command-line information from this device"""
        log.info("Processing the uname -a info for device %s" % device.id)
        om = self.objectMap()
        om.snmpDescr = results.strip()
        om.setHWProductKey, om.snmpSysName, kernelRelease = results.split()[:3]
        om.setOSProductKey = " ".join([om.setHWProductKey, kernelRelease])
        log.debug("snmpSysName=%s, setOSProductKey=%s" % (
                om.snmpSysName, om.setOSProductKey))
        return om
