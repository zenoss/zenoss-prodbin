#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Remove zCountProcs property from all devices.

'''

__version__ = "$Revision$"[11:-2]

import Migrate

class NoCountProcs(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
       for p in dmd.Processes.getSubOSProcessClassesGen():
           try:
               p._delProperty('zCountProcs')
           except ValueError, ex:       # property does not exist
               pass
       for d in dmd.Devices.getSubDevices():
           for p in d.os.processes():
               try:
                   p._delProperty('zCountProcs')
               except ValueError, ex:
                   pass
NoCountProcs()
