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

__doc__ = """ChangeSnmpDefaults

Change zSnmpVer, zSnmpTries and zSnmpTimeout
"""

import Migrate

class ChangeSnmpDefaults(Migrate.Step):
    version = Migrate.Version(4, 2, 0)

    def cutover(self, dmd):

        # only update the props if they are still the defaults
        if dmd.Devices.zSnmpVer == 'v1':
            dmd.Devices._updateProperty('zSnmpVer', 'v2c')
        if dmd.Devices.zSnmpTries == 2:
            dmd.Devices._updateProperty('zSnmpTries', 6)
        if dmd.Devices.zSnmpTimeout == 2.5:
            dmd.Devices._updateProperty('zSnmpTimeout', 1)

ChangeSnmpDefaults()

