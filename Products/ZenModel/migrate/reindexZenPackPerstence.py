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

import Globals
import Migrate
from Products.ZenModel.RRDTemplate import YieldAllRRDTemplates
from Products.ZenModel.ZenPackPersistence import ZenPackPersistence

class ReindexZenPackPerstence(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for t in YieldAllRRDTemplates(dmd):
            for ds in t.datasources():
                if isinstance(ds, ZenPackPersistence):
                    ds.index_object()

ReindexZenPackPerstence()
