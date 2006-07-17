import Migrate
class MaintenanceWindowRelations(Migrate.Step):
    version = 22.0

    def cutover(self, dmd):
        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()


MaintenanceWindowRelations()
