#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add zCollectorDecoding to DeviceClass.

$Id:$
'''
import Migrate

class ZCollectorDecoding(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zCollectorDecoding"):
            dmd.Devices._setProperty("zCollectorDecoding", 'latin-1')

ZCollectorDecoding()
