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
__doc__='''

Add relations for maintenance windows and admin roles.

'''

import Migrate

class MaintenanceWindowRelations(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
        for name in ['Devices', 'Systems', 'Groups', 'Locations']:
            org = getattr(dmd, name)
            org.buildRelations()
            for org in org.getSubOrganizers():
                org.buildRelations()
        for us in dmd.ZenUsers.getAllUserSettings():
            us.buildRelations()


MaintenanceWindowRelations()

