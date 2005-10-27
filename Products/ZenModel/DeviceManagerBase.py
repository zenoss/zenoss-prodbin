
import types

class DeviceManagerBase:
    """
    Default implementation of IDeviceManager interface.  This interface
    is implemented by classes that have a device relationship to allow them
    to manage their device relations.
    """

    def moveTargets(self):
        """see IManageDevice"""
        raise NotImplementedError

    
    def getMoveTarget(self, moveTargetName):
        """see IManageDevice"""
        raise NotImplementedError
        

    def moveDevices(self, moveTarget, deviceNames=None, REQUEST=None):
        """see IManageDevice"""
        if not moveTarget or not deviceNames: return self()
        if type(deviceNames) == types.StringType: deviceNames = (deviceNames,)
        target = self.getMoveTarget(moveTarget)
        for devname in deviceNames:
            dev = self.devices._getOb(devname)
            self.devices.removeRelation(dev)
            target.devices.addRelation(dev)
        if REQUEST:
            REQUEST['RESPONSE'].redirect(target.getPrimaryUrlPath())
    

    def removeDevices(self, deviceNames=None, REQUEST=None):
        """see IManageDevice"""
        if not deviceNames: return self()
        if type(deviceNames) == types.StringType: deviceNames = (deviceNames,)
        for devname in deviceNames:
            self.devices._delObject(devname)
        if REQUEST: return self()
