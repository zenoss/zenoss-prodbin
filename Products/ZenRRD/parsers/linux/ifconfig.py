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

class ifconfig(ComponentCommandParser):

    componentSplit = '\n\n'

    componentScanner = '^(?P<component>.*)[ \t]+Link '

    scanners = [
        r' RX packets:(?P<ifInPackets>\d+) errors:(?P<ifInErrors>\d+)',
        r' TX packets:(?P<ifOutPackets>\d+) errors:(?P<ifOutErrors>\d+)',
        r' RX bytes:(?P<ifInOctets>\d+) ',
        r' TX bytes:(?P<ifOutOctets>\d+) ',
        ]

    componentScanValue = 'interfaceName'
    
