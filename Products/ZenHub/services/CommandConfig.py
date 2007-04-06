from PerformanceConfig import PerformanceConfig

class CommandConfig(PerformanceConfig):

    def remote_getDataSourceCommands(self, *args, **kwargs):
        return self.config.getDataSourceCommands(*args, **kwargs)

    def getDeviceConfig(self, device):
        return device.getDataSourceCommands()

    def sendDeviceConfig(self, listener, config):
        listener.callRemote('updateConfig', config)

    def update(self, object):
        from Products.ZenModel.RRDDataSource import RRDDataSource
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'COMMAND':
                return

        PerformanceConfig.update(self, object)
        
