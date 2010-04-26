###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2010, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__ = """
Change the 'Collector Plugins' menu item to more accurately reflect
the fact that it actually manipulates *modeler* plugins.
"""

import Migrate

class renameMenuToModelerPlugins(Migrate.Step):
    version = Migrate.Version(2, 6, 0)
    
    def cutover(self, dmd):
        items = dmd.zenMenus._getOb('More').zenMenuItems
        pluginsMenuItem = getattr(items, 'collectorPlugins', None)
        if pluginsMenuItem:
            pluginsMenuItem.description = "Modeler Plugins"

renameMenuToModelerPlugins()
