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

__doc__ = """CommandParser

CommandParser parses the output of a command to return a datamap

$Id: CiscoDhcpHelperAddress.py,v 1.3 2003/10/02 19:05:28 edahl Exp $"""

__version__ = '$Revision: 1.3 $'[11:-2]

import re

from Products.ZenModel.IpAddress import findIpAddress

from CommandParser import CommandParser

class CiscoDhcpHelperAddress(CommandParser):
    
    command = 'show run | include helper-address'

    def condition(self, device, log):
        return "UBR" in device.getPrimaryPath()


    def parse(self, device, results, log):
        dhcpips = {}
        findip = re.compile('(\d+\.\d+\.\d+\.\d+)$').search
        for line in results.split('\n'):
            m = findip(line) 
            if m:
                ip = m.group(1)
                dhcpips[ip] = 1
        om = self.newObjectMap() 
        om['setDhcpHelpers'] = dhcpips.keys()
        return om


    def description(self):
        return "Collect dhcp helper servers that a UBR uses"
