#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

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
