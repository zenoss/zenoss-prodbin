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
        from Products.ZenEvents.DbConnectionPool import DbConnectionPool
        cpool = DbConnectionPool()
        conn = cpool.get(backend=self.dmd.ZenEventManager.backend, 
                        host=self.dmd.ZenEventManager.host, 
                        port=self.dmd.ZenEventManager.port, 
                        username=self.dmd.ZenEventManager.username, 
                        password=self.dmd.ZenEventManager.password, 
                        database=self.dmd.ZenEventManager.database)
        curs = conn.cursor()
        try:
            for name in 'zenagios', 'zencacti':
                curs.execute('DELETE FROM heartbeat where component = "%s"' % name)
        finally:
            curs.close()
            cpool.put(conn)

Commands()
