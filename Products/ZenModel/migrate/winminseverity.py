__doc__='''

Add zWinEventlogMinSeverity to DeviceClass.

'''
import Migrate

class WinMinSeverity(Migrate.Step):
    version = Migrate.Version(0, 22, 0)

    def cutover(self, dmd):
	if not dmd.Devices.hasProperty("zWinEventlogMinSeverity"):
            dmd.Devices._setProperty("zWinEventlogMinSeverity", 2, type="int")


WinMinSeverity()
