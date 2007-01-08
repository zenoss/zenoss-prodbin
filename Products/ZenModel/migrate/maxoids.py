#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add zMaxOIDPerRequest to DeviceClass.

$Id:$
'''
import Migrate

class MaxOIDPerRequest(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zMaxOIDPerRequest"):
            dmd.Devices._setProperty("zMaxOIDPerRequest", 40)

MaxOIDPerRequest()
