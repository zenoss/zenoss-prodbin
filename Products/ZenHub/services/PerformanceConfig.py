from HubService import HubService

class PerformanceConfig(HubService):

    def _getOb(self):
        return self.dmd.Monitors.Performance._getOb(self.instance)

    def remote_getDevices(self, devices=None):
        return self._getOb().getDevices(devices)

    def remote_getDeviceUpdates(self, devices):
        return self._getOb().getDeviceUpdates(devices)

    def remote_propertyItems(self):
        return self._getOb().propertyItems()
        
    def remote_getSnmpStatus(self, *args, **kwargs):
        return self._getOb().getSnmpStatus(*args, **kwargs)

