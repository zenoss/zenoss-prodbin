

class IDeviceManager:
    """
    Interface implemented for objects taht manage devices, like DeviceOrganizers
    or monitor configurations.
    """

    def moveTargets(self):
        """
        Return a list of potential targets to which a device can be moved.
        Should remove self from of list.
        """

    def getMoveTarget(self, moveTargetName):
        """
        Return the moveTarget based on its name.
        """

    def moveDevices(self, moveTarget, deviceNames=None, REQUEST=None):
        """
        Move a list of devices from this DeviceManager to another.
        """

    def removeDevices(self, deviceNames=None, REQUEST=None):
        """
        Remove devices from this DeviceManager.
        """
