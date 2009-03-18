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

"""Adds Server/Ssh
"""

import Migrate

class addUnixMonitoring(Migrate.Step):
    version = Migrate.Version(2, 4, 0)

    def cutover(self, dmd):
        if not hasattr(dmd.Devices.Server, 'Ssh'):
            dmd.Devices.Server.manage_addOrganizer('Ssh')
            dmd.Devices.Server.Ssh.zSnmpMonitorIgnore = True
            dmd.Devices.Server.Ssh.zCollectorPlugins = []
            dmd.Devices.Server.Ssh.manage_addRRDTemplate('Device')

addUnixMonitoring()
