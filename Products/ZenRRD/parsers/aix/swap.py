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

class swap(CommandParser):
    
    def processResults(self, cmd, result):
        output = cmd.result.output
        dps = dict([(dp.id, dp) for dp in cmd.points])
        match = re.search('allocated *= *(\d+) blocks *'
                          'used *= *(\d+) blocks *'
                          'free *= * (\d+) blocks', output)
        for i, name in enumerate(
            ['hrSwapSize', 'memUsedSwap', 'memAvailSwap']):
            dp = dps.get(name, None)
            if dp:
                result.values.append( (dp, float(match.group(i + 1)) * 4096) )
        return result
