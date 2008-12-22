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

from Products.ZenRRD.CommandParser import CommandParser
import re

class free(CommandParser):
    
    def processResults(self, cmd, result):
        output = cmd.result.output
        dps = dict([(dp.id, dp) for dp in cmd.points])
        match = re.search('Mem: ' + ' +([0-9]+)' * 6  , output)
        if match:
            for i, dp in enumerate(['hrMemorySize',
                                    'memUsed',
                                    'memAvailReal',
                                    'memShared',
                                    'memBuffer',
                                    'memCached']):
                if dp in dps:
                    result.values.append((dps[dp], float(match.group(i + 1))))
        match = re.search('Swap: ' + ' +([0-9]+)' * 3  , output)
        if match:
            for i, dp in enumerate(['hrSwapSize',
                                    'memUsedSwap',
                                    'memAvailSwap']):
                if dp in dps:
                    result.values.append( (dps[dp], float(match.group(i + 1))) )
        return result
