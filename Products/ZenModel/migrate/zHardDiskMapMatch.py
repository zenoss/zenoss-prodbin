###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Add zHardDiskMapMatch to DeviceClass.

'''
import Migrate

class zHardDiskMapMatch(Migrate.Step):
    version = Migrate.Version(2, 3, 0)
    
    def cutover(self, dmd):
        #if dmd.Devices.hasProperty('zHardDiskMapMatch'):
        #    return

        dmd.Devices._setProperty('zHardDiskMapMatch',
                '', 'string', 'Regex that disks must match to be modeled', True)

        try:
            dmd.Devices.Server.Windows._setProperty('zHardDiskMapMatch', '.*')
        except AttributeError:
            pass

        try:
            dmd.Devices.Server.Linux._setProperty('zHardDiskMapMatch',
                    '^[hs]d[a-z]\d+$|c\d+t\d+d\d+s\d+$|^cciss\/c\dd\dp\d$|' \
                    '^dm\-\d$')
        except AttributeError:
            pass

zHardDiskMapMatch()

