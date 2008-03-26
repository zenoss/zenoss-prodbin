###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information plaease visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

import Globals

from Products.ZenModel.MaintenanceWindow import createMaintenanceWindowCatalog

import logging
log = logging.getLogger("zen.migrate")

class MaintenanceWindowCatalog(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):  
        createMaintenanceWindowCatalog(dmd)
        indexit = lambda x:x.index_object()
        print "Indexing maintenance windows. This may take some time..."
        for dev in dmd.Devices.getSubDevicesGen():
            map(indexit, dev.maintenanceWindows())
        for name in 'Systems', 'Locations', 'Groups', 'Devices':
            organizer = getattr(dmd, name)
            for c in organizer.getSubOrganizers():
                map(indexit, dev.maintenanceWindows())
            map(indexit, organizer.maintenanceWindows())

MaintenanceWindowCatalog()
