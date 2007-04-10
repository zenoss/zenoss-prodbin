__doc__='''

Add zWinServices to !DeviceClass.

$Id:$
'''
import Migrate

class zWinServices(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zWinServices"):
            dmd.Devices._setProperty("zWinServices", False, type="boolean")
            dmd.Devices.Server.Windows._setProperty("zWinServices", True, type="boolean")

zWinServices()