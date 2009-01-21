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


import re
import logging

from Products.ZenRRD.CommandParser import CommandParser


log = logging.getLogger("zen.zencommand")


class uptime(CommandParser):
    
    uptimePattern = re.compile(r' up +((\d+) days, +)?((\d+):)?(\d+)')
    
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
            up 5 days, 1:42    => 5 days, 1 hour, 42 minutes
            up 3 days, 6 min,  => 3 days, 0 hour,  6 minutes
            up 1:14            => 0 days, 1 hour, 14 minutes
            up 4 min,          => 0 days, 0 hour,  4 minutes
        """
        
        match = self.uptimePattern.search(output)
        
        if match:
            days = int(match.group(2) or 0)
            hours = int(match.group(4) or 0)
            minutes = int(match.group(5) or 0)
            log.debug("uptime: days=%s, hours=%s, minutes=%s" % (
                    days, hours, minutes))
            uptime = ((days * 24 + hours) * 60 + minutes) * 60 * 100
        else:
            log.debug("uptime: no match")
            uptime = None
        
        return uptime
