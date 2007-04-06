from PerformanceConfig import PerformanceConfig

class SnmpPerfConfig(PerformanceConfig):

    def remote_getDevices(self, devices=None):
        return self.config.getDevices(devices)

    def remote_getDeviceUpdates(self, devices):
        return self.config.getDeviceUpdates(devices)

    def update(self, object):
        if not self.listeners:
            return

        # the PerformanceConf changed
        from Products.ZenModel.PerformanceConf import PerformanceConf
        if isinstance(object, PerformanceConf):
            for listener in self.listeners:
                listener.callRemote('setPropertyItems', object.propertyItems())
            
        # this is how to tell listeners there's a device change
        def notifyAll(device):
            if device.perfServer().id == self.instance:
                cfg = device.getSnmpOidTargets()
                for listener in self.listeners:
                    listener.callRemote('updateDeviceConfig', cfg)

        # a device changed
        from Products.ZenModel.Device import Device
        if isinstance(object, Device):
            notifyAll(object)
            
        # the template changed
        from Products.ZenModel.RRDDataSource import RRDDataSource
        from Products.ZenModel.RRDDataPoint import RRDDataPoint
        from Products.ZenModel.DeviceClass import DeviceClass
        from Acquisition import aq_parent
        if isinstance(object, RRDDataSource):
            if object.sourcetype != 'SNMP':
                return

        while object:
            
            if isinstance(object, DeviceClass):
                for device in object.getSubDevices():
                    notifyAll(device)
                break

            if isinstance(object, Device):
                notifyAll(object)
                break

            object = aq_parent(object)
