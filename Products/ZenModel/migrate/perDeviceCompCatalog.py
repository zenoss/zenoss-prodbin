###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """Switch from one big component catalog to one per device
"""

from Products.ZenModel.migrate import Migrate


class perDeviceCompCatalog(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):
        # Delete the old componentSearch
        if dmd.Devices.hasObject('componentSearch'):
            dmd.Devices._delObject('componentSearch')

        # Reindex components in the new per-device catalogs
        for device in dmd.Devices.getSubDevicesGen():
            if not device.hasObject('componentSearch'):
                device._create_componentSearch()

perDeviceCompCatalog()
