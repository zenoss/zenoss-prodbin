#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

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
