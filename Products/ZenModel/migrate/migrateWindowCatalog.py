###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Clean up the maintenance window catalog after moving to notification
subscriptions.

'''
import Migrate

class MigrateWindowCatalog(Migrate.Step):
    version = Migrate.Version(4, 0, 1)

    def cutover(self, dmd):
        catalog = dmd.maintenanceWindowSearch
        paths = set()
        for b in catalog():
            path = b.getPath()
            if path.startswith('/zport/dmd/ZenUsers'):
                paths.add(path)
        for path in paths:
            catalog.uncatalog_object(path)

MigrateWindowCatalog()
