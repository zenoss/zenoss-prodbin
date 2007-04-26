#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add zLocalIpAddresses and zLocalInterfaceNames to DeviceClass.

$Id:$
'''
import Migrate

class ZLocalIps(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zLocalIpAddresses"):
            dmd.Devices._setProperty("zLocalIpAddresses", 
                '^127|^0\.0|^169\.254|^224')
        if not dmd.Devices.hasProperty("zLocalInterfaceNames"):
            dmd.Devices._setProperty("zLocalInterfaceNames", '^lo|^vmnet')

ZLocalIps()
