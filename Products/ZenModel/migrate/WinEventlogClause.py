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
__doc__ = """ Add zWinEventlogClause to DeviceClass.

Allows queries based of the Windows Event Log rather than just the severity.
"""

import Migrate

class WinEventlogClause(Migrate.Step):
    version = Migrate.Version(2, 6, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zWinEventlogClause"):
            dmd.Devices._setProperty("zWinEventlogClause", '', type="string")

WinEventlogClause()

