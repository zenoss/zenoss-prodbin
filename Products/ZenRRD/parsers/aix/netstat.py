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
from Products.ZenRRD.parsers.darwin.netstat import netstat as darwin_netstat

class netstat(darwin_netstat):

    componentScanner = '^(?P<component>[^ ]*) '
    scanners = [
        r' +(?P<mtu>\d+)'
        r' +link.{34,34}'
        r' +(?P<ifInPackets>\d+)'
        r' +(?P<ifInErrors>\d+) '
        r' +(?P<ifOutPackets>\d+) '
        r' +(?P<ifOutErrors>\d+) '
        r' +(?P<lastColumn>\d*)-?$',
        ]

