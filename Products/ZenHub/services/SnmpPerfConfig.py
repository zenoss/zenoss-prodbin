from PerformanceConfig import PerformanceConfig

class SnmpPerfConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        return self.config.getDevices(devices)

    def remote_getDeviceUpdates(self, devices):
        return self.config.getDeviceUpdates(devices)
