import Migrate

class DeviceTemplatesProperty(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zDeviceTemplates"):
            dmd.Devices._setProperty("zDeviceTemplates", ["Device"],
                                     type="lines")

DeviceTemplatesProperty()
