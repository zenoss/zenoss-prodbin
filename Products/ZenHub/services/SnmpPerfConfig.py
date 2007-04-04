from PerformanceConfig import PerformanceConfig

class SnmpPerfConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        return self.config.getDevices(devices)

    def remote_getDeviceUpdates(self, devices):
        return self.config.getDeviceUpdates(devices)

    def update(self, object):
        from Products.ZenModel.Device import Device
        if not self.listeners:
            return
        if isinstance(object, Device):
            if object.perfServer().id != self.instance:
                return
            cfg = object.getSnmpOidTargets()
            for listener in self.listeners:
                listener.callRemote('updateDeviceConfig', cfg)
