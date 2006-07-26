__doc__='''

Add zWinEventlogMinSeverity to DeviceClass.

'''
import Migrate
class WinMinSeverity(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
	if dmd.Devices._getOb("zWinEventlogMinSeverity",None) is None:
            dmd.Devices._setProperty("zWinEventlogMinSeverity", 2, type="int")


WinMinSeverity()
