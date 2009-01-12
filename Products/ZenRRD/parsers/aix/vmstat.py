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

class vmstat(CommandParser):
    
    def processResults(self, cmd, result):
        output = cmd.result.output
        dps = dict([(dp.id, dp) for dp in cmd.points])
        match = re.search('mem=([0-9]+)MB', output)
        dp = dps.get('hrMemorySize', None)
        if match and dp:
            result.values.append( (dp, float(match.group(1))*1024*1024) )
        dp = dps.get('memUsed', None) 
        lastLine = output.split('\n')[-2]
        values = map(int, lastLine.split())
        if dp:
            result.values.append( (dp, values[2] * 4096) )
        dp = dps.get('memAvailReal', None)
        if dp:
            result.values.append( (dp, values[3] * 4096) )
        return result
