###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''

Delete the non-working load average report.  Reports will be added back in 1.1.

$Id:$
'''
import Migrate

class LoadAverageReport(Migrate.Step):
    version = Migrate.Version(1,0,0)

    def cutover(self, dmd):
        if hasattr(dmd.Reports, 'Performance Reports'):
            dmd.Reports._delObject("Performance Reports")

LoadAverageReport()


