from PerformanceConfig import PerformanceConfig

class XmlRPCConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        return self.config.getDevices(devices)

    def remote_getDeviceUpdates(self, devices):
        return self.config.getDeviceUpdates(devices)

    def remote_getXmlRpcDevices(self, *args, **kwargs):
        return self.config.getXmlRpcDevices(*args, **kwargs)

    def getDeviceConfig(self, device):
        return device.getXmlRpcTargets()

    def sendDeviceConfig(self, listener, config):
        listener.callRemote('updateDeviceConfig', config)

