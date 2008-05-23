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


class HappierZenPackRels(Migrate.Step):
    version = Migrate.Version(2, 3, 0)

    def cutover(self, dmd):
        for p in dmd.ZenPackManager.packs():
            p.buildRelations() # This is probably not necessary
            p.manager.obj = dmd.ZenPackManager


HappierZenPackRels()
