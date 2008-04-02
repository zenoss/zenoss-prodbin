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
        import maintwindowcatalog, devicepathindex, monitorTemplateMenu, \
                makeTemplateCatalog, networkindexes
        self.dependencies = [ maintwindowcatalog.maintwindowcatalog,
                              devicepathindex.devicepathindex,
                              networkindexes.networkindexes,
                              makeTemplateCatalog.makeTemplateCatalog,
                              monitorTemplateMenu.monitorTemplateMenu ]

    def cutover(self, dmd):  
        indexit = lambda x:x.index_object()
        for dev in dmd.Devices.getSubDevices_recursive():

        # For devicepathindex
            dev.index_object()

        # For maintwindowcatalog
            map(indexit, dev.maintenanceWindows())
            # Index rrdTemplates on the device and its components
            map(indexit, dev.objectValues('RRDTemplate'))
            for comp in dev.getDeviceComponents():
                map(indexit, comp.objectValues('RRDTemplate'))
            
        for name in 'Systems', 'Locations', 'Groups', 'Devices':
            organizer = getattr(dmd, name)
            indexRRDTemplates = name == 'Devices'
            for org in organizer.getSubOrganizers():
                map(indexit, org.maintenanceWindows())
                if indexRRDTemplates:
                    map(indexit, org.rrdTemplates())
            map(indexit, organizer.maintenanceWindows())
            if indexRRDTemplates:
                map(indexit, organizer.rrdTemplates())

        # for networkindexes
        dmd.Networks.reIndex()

        # Need to index the rrdTemplates on perf monitors too
        map(indexit, dmd.Monitors.getAllRRDTemplates())
            

twotwoindexing = TwoTwoIndexing()
