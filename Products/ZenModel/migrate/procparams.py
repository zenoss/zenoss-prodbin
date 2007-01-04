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
