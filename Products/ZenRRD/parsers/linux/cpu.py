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

class cpu(CommandParser):
    def processResults(self, cmd, result):
        output = cmd.result.output
        dps = dict( [(dp.id, dp) for dp in cmd.points] )
        values = output.split('\n')[0].split()[1:]
        columns = ['ssCpuUser',
                   'ssCpuNice',
                   'ssCpuSystem',
                   'ssCpuIdle',
                   'ssCpuWait',
                   'ssCpuInterrupt',
                   'ssCpuSoftInterrupt',
                   'ssCpuSteal']
        if len(values) < len(columns):
            return
        for i, dp in enumerate(columns):
            if dp in dps:
                result.values.append( (dps[dp], long(values[i])) )
            
