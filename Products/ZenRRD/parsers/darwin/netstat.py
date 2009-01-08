###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenRRD.ComponentCommandParser import ComponentCommandParser

class netstat(ComponentCommandParser):

    componentScanner = '^(?P<component>[^ ]*)[*]? '

    scanners = [
        r' +(?P<mtu>\d+) .* '
        r' (?P<ifInPackets>\d+)'
        r' +(?P<ifInErrors>\d*)-?'
        r' +(?P<ifInOctets>\d+)'
        r' +(?P<ifOutPackets>\d+)'
        r' +(?P<ifOutErrors>\d*)-?'
        r' +(?P<ifOutOctets>\d+)'
        r' +(?P<lastColumn>\d*)-?$',
        ]

    componentScanValue = 'interfaceName'
    
    def processResults(self, cmd, result):
        ComponentCommandParser.processResults(self, cmd, result)
