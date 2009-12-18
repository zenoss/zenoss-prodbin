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

from Products.ZenUtils.Search import makePathIndex, makeMultiPathIndex

class UpgradeMultiPathIndices(Migrate.Step):
    version = Migrate.Version(2, 6, 0)

    def cutover(self, dmd):
        idx = dmd.Devices.deviceSearch._catalog.indexes['path']
        idx_parents = getattr(idx, '_index_parents', None)
        if idx_parents is None:
            dmd.Devices.deviceSearch.delIndex('path')
            dmd.Devices.deviceSearch._catalog.addIndex('path', 
                    makeMultiPathIndex('path'))

        idx = dmd.searchRRDTemplates._catalog.indexes['getPhysicalPath']
        if not idx.__class__.__name__=='ExtendedPathIndex':
            templates = dmd.searchRRDTemplates()
            dmd.searchRRDTemplates.delIndex('getPhysicalPath')
            dmd.searchRRDTemplates._catalog.addIndex('getPhysicalPath', 
                    makePathIndex('getPhysicalPath'))

upgradeindices = UpgradeMultiPathIndices()
