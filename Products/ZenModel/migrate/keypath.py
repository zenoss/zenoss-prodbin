#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Add zKeyPath to DeviceClass.

$Id:$
'''
import Migrate

class KeyPath(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zKeyPath"):
            dmd.Devices._setProperty("zKeyPath", "~/.ssh/id_dsa")

KeyPath()