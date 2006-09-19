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

        dmd.Events.createOrganizer("/Status/XmlRpc")
        dmd.Events.createOrganizer("/Perf/Snmp")
        dmd.Events.createOrganizer("/Perf/CPU")
        dmd.Events.createOrganizer("/Perf/Interface")
        dmd.Events.createOrganizer("/Perf/Memory")
        dmd.Events.createOrganizer("/Perf/Filesystem")

PerfXmlRpc()
