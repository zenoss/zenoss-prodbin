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
           if p.hasProperty('zCountProcs'):
               p._delProperty('zCountProcs')
       for d in dmd.Devices.getSubDevices():
           for p in d.os.processes():
               if p.hasProperty('zCountProcs'):
                   p._delProperty('zCountProcs')
       if dmd.Devices.rrdTemplates.hasProperty('OSProcessCount'):
           dmd.Devices.rrdTemplates._delObject('OSProcessCount')

NoCountProcs()
