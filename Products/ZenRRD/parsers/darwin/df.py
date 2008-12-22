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

class df(ComponentCommandParser):

    componentSplit = '\n'

    componentScanner = '% (?P<component>/.*)'

    scanners = [
        r' (?P<totalBlocks>\d+) +(?P<usedBlocks>\d+) '
        r'+(?P<availableBlocks>\d+) +(?P<percentUsed>\d+)% '
        r'+(?P<usedInodes>\d+) +(?P<freeInodes>\d+) '
        r'+(?P<percentInodesUsed>\d+)%'
        ]
    
    componentScanValue = 'mount'

