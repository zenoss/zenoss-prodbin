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

_doc__ = """uname
Determine the Operating System's name from the result of the
uname command.
"""

from CollectorPlugin import CommandPlugin

class uname(CommandPlugin):
    
    maptype = "DeviceMap" 
    compname = "os"
    command = 'uname'

    def process(self, device, results, log):
        """Collect command-line information from this device"""
        log.info("Processing the OS uname info for device %s" % device.id)
        om = self.objectMap()
        om.uname = results.strip()
        log.debug("uname = %s" % om.uname )
        return om


