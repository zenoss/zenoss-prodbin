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
__doc__ = 'add the ReportServer to existing systems'

__version__ = "$Revision$"[11:-2]

import Globals
import Migrate

class ReportServer(Migrate.Step):
    version = Migrate.Version(1, 1, 0)
    
    def cutover(self, dmd):
        from Products.ZenReports.ReportServer import manage_addReportServer
        portal = dmd.getPhysicalRoot().zport
        id = 'ReportServer'
        if not hasattr(portal, id):
            manage_addReportServer(portal, id)

ReportServer()


