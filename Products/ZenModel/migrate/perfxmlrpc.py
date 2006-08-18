__doc__='''

Add zXmlRpcMonitorIgnore to DeviceClass and XmlRpc to EventClass.

'''
import Migrate
class PerfXmlRpc(Migrate.Step):
    version = 23.0

    def cutover(self, dmd):
        if not dmd.Devices.hasProperty("zXmlRpcMonitorIgnore"):
            dmd.Devices._setProperty("zXmlRpcMonitorIgnore", 
                                     False, type="boolean")
        try:
            dmd.Events.getOrganizer("/Status/XmlRpc")
        except KeyError:
            dmd.Events.createOrganizer("/Status/XmlRpc")

PerfXmlRpc()
