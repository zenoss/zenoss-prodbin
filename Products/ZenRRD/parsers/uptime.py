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
    
    uptimePattern = re.compile(r' up ((\d+) days, +)?(\d+)(:(\d+))?')
    
    def processResults(self, cmd, result):
        """
        Parse the results of the uptime command to get sysUptime and load
        averages.
        """
        output = cmd.result.output
        
        dps = dict([(dp.id, dp) for dp in cmd.points])

        if 'sysUpTime' in dps:
            sysUpTime = self.parseSysUpTime(output)
            if sysUpTime:
                result.values.append((dps['sysUpTime'], sysUpTime))
                
        match = re.search(r' load averages?: '
                          r'([0-9.]+),? ([0-9.]+),? ([0-9.]+)$',
                          output)
        if match:
            for i, dp in enumerate(['laLoadInt1', 'laLoadInt5', 'laLoadInt15']):
                if dp in dps:
                    result.values.append( (dps[dp], float(match.group(i + 1))) )
        return result

    def parseSysUpTime(self, output):
        """
        Parse the sysUpTime from the output of the uptime command.  There are
        multiple formats:
            up 5 days, 1:42
            up 3 days, 6 min, 
            up 1:14
            up 4 min, 
        """
        
        match = self.uptimePattern.search(output)
        
        if match:
            uptime = (
                int(match.group(2) or 0) * 24 * 60 * 60 +
                int(match.group(3)) * 60 * 60 +
                int(match.group(5) or 0) * 60
                ) * 100
        else:
            uptime = None
        
        return uptime
