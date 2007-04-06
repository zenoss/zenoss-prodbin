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

    def notifyAll(self, device):
        if device.perfServer().id == self.instance:
            cfg = self.getDeviceConfig(device)
            if cfg is not None:
                for listener in self.listeners:
                    self.sendDeviceConfig(listener, cfg)

    def getDeviceConfig(self, device):
        "How to get the config for a device"
        return None

    def sendDeviceConfig(self, listener, config):
        "How to send the config to a device, probably via callRemote"
        pass

    def update(self, object):
        if not self.listeners:
            return

        # the PerformanceConf changed
        from Products.ZenModel.PerformanceConf import PerformanceConf
        if isinstance(object, PerformanceConf):
            for listener in self.listeners:
                listener.callRemote('setPropertyItems', object.propertyItems())
            
        # somethinge else... hunt around for some devices
        from Products.ZenModel.Device import Device
        from Products.ZenModel.DeviceClass import DeviceClass
        from Acquisition import aq_parent

        while object:
            # walk up until you hit an organizer or a device
            if isinstance(object, DeviceClass):
                for device in object.getSubDevices():
                    self.notifyAll(device)
                break

            if isinstance(object, Device):
                self.notifyAll(object)
                break

            object = aq_parent(object)
