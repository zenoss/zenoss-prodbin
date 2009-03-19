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

"""Adds Server/SSH and Server/SSH/Linux device classes
"""

import Migrate

class addUnixMonitoring(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.Devices.Server, 'SSH'):
            dmd.Devices.Server.manage_addOrganizer('SSH')
            dmd.Devices.Server.SSH.zSnmpMonitorIgnore = True
            dmd.Devices.Server.SSH.zCollectorPlugins = []
            dmd.Devices.Server.SSH.manage_addRRDTemplate('Device')
        if not hasattr(dmd.Devices.Server.SSH, 'Linux'):
            dmd.Devices.Server.SSH.manage_addOrganizer('Linux')

addUnixMonitoring()
