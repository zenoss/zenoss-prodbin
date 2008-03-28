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

from Products.CMFCore.utils import getToolByName
from Products.ZenUtils.Search import makeMultiPathIndex
from Products.ZCatalog.Catalog import CatalogError

import logging
log = logging.getLogger("zen.migrate")

class DevicePathIndex(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):  
        cat = getToolByName(dmd.Devices, 'deviceSearch')
        try:
            cat._catalog.addIndex('path', makeMultiPathIndex('path'))
        except CatalogError:
            # Index already exists
            pass

devicepathindex = DevicePathIndex()
