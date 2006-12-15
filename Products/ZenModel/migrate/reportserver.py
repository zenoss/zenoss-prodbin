#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
__doc__ = 'add the ReportServer to existing systems'

__version__ = "$Revision$"[11:-2]

import Globals
import Migrate

class ReportServer(Migrate.Step):
    version = Migrate.Version(1, 0, 3)
    
    def cutover(self, dmd):
        from Products.ZenReports.ReportServer import manage_addReportServer
        portal = dmd.getPhysicalRoot().zport
        id = 'ReportServer'
        if not hasattr(portal, id):
            manage_addReportServer(portal, id)

ReportServer()

