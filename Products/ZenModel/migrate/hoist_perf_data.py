#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Move the perf data out of the category-based directories and into a
single namespace.

$Id$
'''

__version__ = "$Revision$"[11:-2]


import Migrate

import os

class HoistPerfData(Migrate.Step):
    version = 21.0

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
                root = os.path.join(oldbase, name)
                try:
                    for f in os.listdir(root):
                        oldname = os.path.join(root, f)
                        newname = os.path.join(oldbase, f)
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
