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
from ZenScriptBase import ZenScriptBase

PATHS = (

    # Tools
    '/zport/RenderServer',
    '/zport/ReportServer',
    '/zport/ZenTableManager',
    '/zport/ZenPortletManager',
    '/zport/dmd/DeviceLoader',
    '/zport/dmd/ZenEventManager',
    '/zport/dmd/ZenEventHistory',
    '/zport/dmd/ZenUsers',
    '/zport/dmd/ZenLinkManager',
    '/zport/dmd/ZenPackManager',

    # Catalogs
    '/zport/dmd/Devices/deviceSearch',
    '/zport/dmd/Devices/componentSearch',
    '/zport/dmd/maintenanceWindowSearch',
    '/zport/dmd/searchRRDTemplates',
    '/zport/dmd/zenPackPersistence',
    '/zport/dmd/Networks/ipSearch',

    # Organizers and other trees
    '/zport/dmd/Locations',
    '/zport/dmd/Systems',
    '/zport/dmd/Groups',
    '/zport/dmd/Devices',
    '/zport/dmd/Devices/Server',
    '/zport/dmd/Devices/Server/Linux',

    '/zport/dmd/Networks',
    '/zport/dmd/Mibs',
    '/zport/dmd/Monitors',
    '/zport/dmd/Processes',

    '/zport/dmd/Manufacturers',
    '/zport/dmd/Manufacturers/Microsoft',

    '/zport/dmd/Services',
    '/zport/dmd/Services/WinService',
    '/zport/dmd/Services/IpService',
    '/zport/dmd/Services/IpService/Privileged',

    '/zport/dmd/Events',
    '/zport/dmd/Events/Status',
    '/zport/dmd/Events/Status/Ping'
)

class BadInstallError(Exception):
    """
    The database wasn't loaded correctly.
    """

class CheckBasicInstall(ZenScriptBase):

    def check(self):
        _allgood = True
        for path in PATHS:
            try:
                ob = self.dmd.unrestrictedTraverse(path)
            except KeyError:
                self.log.critical(' Object %s not found.' % path)
                _allgood = False
        if not _allgood:
            raise BadInstallError, 'This Zenoss database was not built properly.'


if __name__ == "__main__":
    tmbk = CheckBasicInstall(connect=True)
    tmbk.check()
