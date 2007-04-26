import Migrate
from Acquisition import aq_base

class zCollectorPlugins(Migrate.Step):
    version = Migrate.Version(2, 0, 0)

    def cutover(self, dmd):
        if not hasattr(aq_base(dmd.Devices), 'zCollectorPlugins'):
            dmd.Devices._setProperty("zCollectorPlugins", [], type='lines')

zCollectorPlugins()
 




