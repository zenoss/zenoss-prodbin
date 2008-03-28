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

import logging
log = logging.getLogger("zen.migrate")

class TwoTwoIndexing(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import maintwindowcatalog, devicepathindex
        self.dependencies = [ maintwindowcatalog.maintwindowcatalog,
                              devicepathindex.devicepathindex ]

    def cutover(self, dmd):  
        indexit = lambda x:x.index_object()
        for dev in dmd.Devices.getSubDevices_recursive():
            # For devicepathindex
            dev.index_object()
            # For maintwindowcatalog
            map(indexit, dev.maintenanceWindows())
        for name in 'Systems', 'Locations', 'Groups', 'Devices':
            organizer = getattr(dmd, name)
            for org in organizer.getSubOrganizers():
                map(indexit, org.maintenanceWindows())
            map(indexit, organizer.maintenanceWindows())

twotwoindexing = TwoTwoIndexing()
