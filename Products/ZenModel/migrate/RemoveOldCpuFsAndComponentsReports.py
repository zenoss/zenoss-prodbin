###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Delete the previous CPU Util, FS Util and All Monitored Components reports.  
The slightly modified ones will get loaded at the end of migration.

$Id:$
'''
import Migrate

class RemoveOldCpuFsAndComponentsReports(Migrate.Step):
    version = Migrate.Version(3,0,0)

    def cutover(self, dmd):
        if hasattr(dmd.Reports, 'Performance Reports'):
            perfReports = dmd.Reports['Performance Reports']

            if hasattr(perfReports, 'CPU Utilization'):
                perfReports._delObject('CPU Utilization')
            if hasattr(perfReports, 'Filesystem Util Report'):
                perfReports._delObject('Filesystem Util Report')

        if hasattr(dmd.Reports, 'Device Reports'):
            devReports = dmd.Reports['Device Reports']

            if hasattr(devReports, 'All Monitored Components'):
                devReports._delObject('All Monitored Components')

RemoveOldCpuFsAndComponentsReports()


