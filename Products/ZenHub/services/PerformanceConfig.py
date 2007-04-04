from HubService import HubService

class PerformanceConfig(HubService):

    def __init__(self, dmd, instance):
        HubService.__init__(self, dmd, instance)
        self.config = self.dmd.Monitors.Performance._getOb(self.instance)

    def remote_propertyItems(self):
        return self.config.propertyItems()
        
    def remote_getSnmpStatus(self, *args, **kwargs):
        return self.config.getSnmpStatus(*args, **kwargs)

    def remote_getDefaultRRDCreateCommand(self, *args, **kwargs):
        return self.config.getDefaultRRDCreateCommand(*args, **kwargs)
