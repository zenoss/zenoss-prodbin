__doc__='''

Add zNagiosPath and zNagiosCycleTime to DeviceClass.

'''
import Migrate
class Nagios(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
	if not dmd.Devices.hasProperty("zNagiosPath"):
		dmd.Devices._setProperty("zNagiosPath",'/usr/local/nagios/libexec',)
	if not dmd.Devices.hasProperty("zNagiosCycleTime"):
		dmd.Devices._setProperty("zNagiosCycleTime",60,type='int')

Nagios()
