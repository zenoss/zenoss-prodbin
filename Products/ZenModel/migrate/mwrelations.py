import Migrate
class MaintenanceWindowRelations(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
        for us in dmd.ZenUsers.getAllUserSettings():
            us.buildRelations()


MaintenanceWindowRelations()
