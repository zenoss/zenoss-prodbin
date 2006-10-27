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

def delProperty(obj, name):
    try:
        obj._delProperty(name)
    except (ValueError, AttributeError), ex:
        pass

class NoCountProcs(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def cutover(self, dmd):
       for p in dmd.Processes.getSubOSProcessClassesGen():
           delProperty(p, 'zCountProcs')
       for d in dmd.Devices.getSubDevices():
           for p in d.os.processes():
               delProperty(p, 'zCountProcs')
       delProperty(dmd.Devices.rrdTemplates, 'OSProcessCount')

NoCountProcs()
