__doc__='''

Add relations for maintenance windows and admin roles.

'''

import Migrate
class MaintenanceWindowRelations(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
        for name in 'Devices', 'Systems', 'Groups', 'Locations':
            org = getattr(dmd, name)
            org.buildRelations()
            for org in org.getSubOrganizers():
                org.buildRelations()
        for us in dmd.ZenUsers.getAllUserSettings():
            us.buildRelations()


MaintenanceWindowRelations()
