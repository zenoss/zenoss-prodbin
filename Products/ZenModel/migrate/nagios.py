__doc__='''

Add zNagiosPath and zNagiosCycleTime to DeviceClass.

'''
import Migrate
class Nagios(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
        import os
	if not dmd.Devices.hasProperty("zNagiosPath"):
            path = os.path.join(os.environ['ZENHOME'], 'libexec')
            dmd.Devices._setProperty("zNagiosPath", path)
                                         )
	if not dmd.Devices.hasProperty("zNagiosCycleTime"):
            dmd.Devices._setProperty("zNagiosCycleTime",60,type='int')

Nagios()
