###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Migrate
from Products.Zuul.catalog.global_catalog import createGlobalCatalog

class GlobalCatalog(Migrate.Step):
    version = Migrate.Version(3, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import reindexdevices
        self.dependencies = [reindexdevices.upgradeindices]

    def cutover(self, dmd):
        zport = dmd.getPhysicalRoot().zport

        if getattr(zport, 'global_catalog', None) is None:

            # Create the catalog
            createGlobalCatalog(zport)


GlobalCatalog()
