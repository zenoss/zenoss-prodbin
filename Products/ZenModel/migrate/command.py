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

Add zCommandPath and zCommandCycleTime to DeviceClass.

'''
import Migrate

class Commands(Migrate.Step):
    version = Migrate.Version(0, 23, 0)

    def update(self, dmd, oldname, name, default, **kw):
        if dmd.Devices.hasProperty(oldname):
            value = not dmd.Devices.getProperty(oldname)
            dmd.Devices._setProperty(name, value, **kw)
            dmd.Devices._delProperty(oldname)
        elif not dmd.Devices.hasProperty(name):
            dmd.Devices._setProperty(name, default, **kw)
        
    def cutover(self, dmd):
        import os
        self.update(dmd, "zNagiosPath", "zCommandPath",
                    os.path.join(os.environ['ZENHOME'], 'libexec'))
        if dmd.Devices.hasProperty("zNagiosCycleTime"):
            dmd.Devices._delProperty("zNagiosCycleTime")
        zem = self.dmd.ZenEventManager
        conn = zem.connect()
        try:
            curs = conn.cursor()
            for name in 'zenagios', 'zencacti':
                curs.execute('DELETE FROM heartbeat where component = "%s"' % name)
        finally: zem.close(conn)

Commands()
