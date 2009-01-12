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

class mpstat(CommandParser):

    
    
    def processResults(self, cmd, result):
        output = cmd.result.output
        cols = output.split('\n')[-2].split()
        dps = dict([(dp.id, dp) for dp in cmd.points])
        for dp, col in [('ssCpuUser', 23),
                        ('ssCpuSystem', 24),
                        ('ssCpuWait', 25),
                        ('ssCpuIdle', 26),
                        ('ssRawContexts', 9),
                        ('ssRawInterrupts', 10)]:
            dp = dps[dp]
            if dp:
                result.values.append( (dp, float(cols[col])) )
        return result
