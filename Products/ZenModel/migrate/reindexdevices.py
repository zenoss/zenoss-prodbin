###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
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

from Products.ZenUtils.Search import makePathIndex

class ReindexDevicesAndTemplates(Migrate.Step):
    version = Migrate.Version(2, 6, 0)

    def cutover(self, dmd):  
        idx = dmd.Devices.deviceSearch._catalog.indexes['path']
        if not getattr(idx, '_index_parents') or not len(idx._index_parents):
            for dev in dmd.Devices.getSubDevices():
                dev.index_object()

        idx = dmd.searchRRDTemplates._catalog.indexes['getPhysicalPath']
        if not idx.__class__.__name__=='ExtendedPathIndex':
            templates = dmd.searchRRDTemplates()
            dmd.searchRRDTemplates.delIndex('getPhysicalPath')
            dmd.searchRRDTemplates._catalog.addIndex('getPhysicalPath', 
                    makePathIndex('getPhysicalPath'))
            for brain in templates:
                try:
                    brain.getObject().index_object()
                except KeyError:
                    # This shouldn't happen, but in case they have a
                    # bad catalog let's try not to die
                    pass

ReindexDevicesAndTemplates()
