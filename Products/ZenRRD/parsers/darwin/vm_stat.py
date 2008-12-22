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

class vm_stat(CommandParser):

    def processResults(self, cmd, results):
        import re
        output = cmd.result.output
        match = re.search('page size of (\d+) bytes', output)
        if match:
            pageSize = int(match.group(1))
            match = re.search('Pages free: * (\d+)', output)
            if match:
                for dp in cmd.points:
                    if dp.id == 'freeMemory':
                        results.values.append(
                            (dp, int(match.group(1))*pageSize)
                            )
                        break
