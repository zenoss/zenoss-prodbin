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

Reexecute zenprocs.sql to get new version of procedures (now parameterized)

'''
import Migrate

class ProcParams(Migrate.Step):
    version = Migrate.Version(1, 1, 0)

    def cutover(self, dmd):
        import os
        import os.path
        procs = os.path.join(
                    os.environ['ZENHOME'], 'Products', 'ZenEvents', 'db', 'zenprocs.sql')
        os.system('cat %s | mysql -u%s -p%s %s' % (
                    procs,
                    dmd.ZenEventManager.username,
                    dmd.ZenEventManager.password,
                    dmd.ZenEventManager.database))
        

ProcParams()

