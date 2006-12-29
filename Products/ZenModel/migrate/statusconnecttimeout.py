#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add zStatusConnectTimeout to DeviceClass.

$Id:$
'''
import Migrate

class StatusConnectTimeout(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zStatusConnectTimeout"):
            dmd.Devices._setProperty("zStatusConnectTimeout", 
                                     15.0, type="float")

StatusConnectTimeout()
