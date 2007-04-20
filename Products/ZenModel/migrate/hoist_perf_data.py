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

Move the perf data out of the category-based directories and into a
single namespace.

'''

__version__ = "$Revision$"[11:-2]


import Migrate

import os

class HoistPerfData(Migrate.Step):
    version = Migrate.Version(0, 21, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        self.renames = []

    def cutover(self, dmd):
        import glob
        names = dmd.getDmdRoot('Devices').getOrganizerNames(True)
        
        oldbase = os.path.join(os.getenv('ZENHOME'), 'perf', 'Devices')
        names.sort()
        names.reverse()
        for name in names:
            if name and name != '/':
                name = name.lstrip('/')
                root = os.path.join(oldbase, name, "devices")
                try:
                    for f in os.listdir(root):
                        oldname = os.path.join(root, f)
                        newname = os.path.join(oldbase, f)
                        if os.path.isdir(newname): continue
                        os.renames(oldname, newname)
                        self.renames.append( (oldname, newname) )
                except OSError, err:
                    import errno
                    n, msg = err.args
                    if n != errno.ENOENT:
                        raise err

    def revert(self):
        for oldname, newname in self.renames:
            os.renames(newname, oldname)

HoistPerfData()
