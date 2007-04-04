from PerformanceConfig import PerformanceConfig

class CommandConfig(PerformanceConfig):

    def remote_getDataSourceCommands(self, *args, **kwargs):
        return self.config.getDataSourceCommands(*args, **kwargs)

