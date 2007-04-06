from PerformanceConfig import PerformanceConfig

class SnmpPerfConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        return self.config.getDevices(devices)

    def remote_getDeviceUpdates(self, devices):
        return self.config.getDeviceUpdates(devices)

    def getDeviceConfig(self, device):
        return device.getSnmpOidTargets()

    def sendDeviceConfig(self, listener, config):
        listener.callRemote('updateDeviceConfig', config)

    def update(self, object):
        from Products.ZenModel.RRDDataSource import RRDDataSource
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'SNMP':
                return

        PerformanceConfig.update(self, object)
