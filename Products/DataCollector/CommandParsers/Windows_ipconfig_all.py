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

$Id: Uname_A.py,v 1.2 2003/10/01 23:40:51 edahl Exp $"""

__version__ = '$Revision: 1.2 $'[11:-2]

from CommandParser import CommandParser

class Windows_ipconfig_all(CommandParser):
    
    command = 'ipconfig /all'

    def condition(self, device, log):
        pp = device.getPrimaryPath()
        return "Windows" in pp

    def parse(self, device, results, log):
        log.info('Collecting interfaces for device %s' % device.id)
        rm = self.newRelationshipMap("interfaces")
        rlines = results.split("\n")
        # normalize on address 0.0.0.0 means all addresses
        for line in rlines:
            try:
            except ValueError:
                log.exception("failed to parse ipservice information")
            om = self.newObjectMap("ZenModel.IpInterface")
            om['id'] = "-".join((addr, proto, port))
            om['ipaddress'] = addr
            om['setPort'] = port
            om['setProtocol'] = proto
            om['discoveryAgent'] = 'IpServiceMap-' + __version__
            rm.append(om)
            log.debug('Adding TCP Service %s %s' % (addr, port))
        return rm

    def description(self):
        return "run netstat -an on server to build ipservices"
