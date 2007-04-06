from PerformanceConfig import PerformanceConfig

class ProcessConfig(PerformanceConfig):

    def remote_getOSProcessConf(self, devices=None):
        return self.config.getOSProcessConf(devices)

    def remote_getProcessStatus(self, devices=None):
        return self.config.getProcessStatus(devices)

    def getDeviceConfig(self, device):
        return device.getOSProcessConf()

    def sendDeviceConfig(self, listener, config):
        listener.callRemote('updateDevice', config)

