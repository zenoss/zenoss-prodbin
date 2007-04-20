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
