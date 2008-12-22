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

class uptime(CommandParser):
    
    def processResults(self, cmd, result):
        output = cmd.result.output
        match = re.search(r' up (\d+) days, (\d+)(:(\d+))?', output)
        dps = dict([(dp.id, dp) for dp in cmd.points])
        if match:
            uptime = (
                int(output.group(1)) * 24 * 60 * 60 +
                int(output.group(2)) * 60 * 60 +
                int(output.group(3) or '0') * 60
                ) * 100
            if 'sysUpTime' in dps:
                result.values.append( (dps['sysUpTime'], uptime) )
        match = re.search(r' load averages?: '
                          r'([0-9.]+),? ([0-9.]+),? ([0-9.]+)$',
                          output)
        if match:
            for i, dp in enumerate(['laLoadInt1', 'laLoadInt5', 'laLoadInt15']):
                if dp in dps:
                    result.values.append( (dps[dp], float(match.group(i + 1))) )
        return result
