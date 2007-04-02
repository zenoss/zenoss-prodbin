import Migrate

class zCollectorPlugins(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    def cutover(self, dmd):
        dmd.Devices._setProperty("zCollectorPlugins", [], type='lines')

 zCollectorPlugins()
 




