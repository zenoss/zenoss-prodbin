__doc__='Add commands to EventManager'

import Migrate

class EventNewClasses(Migrate.Step):
    version = Migrate.Version(1, 1, 0)
    
    def cutover(self, dmd):
        dmd.Events.createOrganizer("/Perf/XmlRpc")
        dmd.Events.createOrganizer("/Status/Perf")
        dmd.Events.createOrganizer("/Status/Update")
        dmd.ZenEventManager.buildRelations()

EventNewClasses()
