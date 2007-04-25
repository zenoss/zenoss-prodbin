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

Add zWmiMonitorIgnore to DeviceClass.

$Id:$
'''
import Migrate

class WmiIgnore(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zWmiMonitorIgnore"):
            dmd.Devices._setProperty("zWmiMonitorIgnore", 
                                     False, type="boolean")

WmiIgnore()


