
import Migrate

class WinModelerUnderModeler(Migrate.Step):

    version = Migrate.Version(2, 2, 0)
    
    def cutover(self, dmd):
        import os
        from Products.ZenUtils.Utils import zenPath
        os.system('%s stop >/dev/null 2>&1' % zenPath('bin', 'zenwinmodeler'))
        conn = dmd.ZenEventManager.connect()
        curr = conn.cursor()
        curr.execute("delete from heartbeat where component = 'zenwinmodeler'")

WinModelerUnderModeler()
