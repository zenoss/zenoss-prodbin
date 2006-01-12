

class IDeviceManager:
    """
    Interface implemented for objects taht manage devices, like DeviceOrganizers
    or monitor configurations.
    """

    def deviceMoveTargets(self):
        """
        Return a list of potential targets to which a device can be moved.
        Should remove self from of list.
        """

    def getDeviceMoveTarget(self, moveTargetName):
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


class IEventView:
    """
    IEventView interface controls how event lists are built for an object.
    """
    
    def eventWhere(self):
        """
        Return a where clause that will find events for this object.
        """

    def eventOrderby(self):
        """
        Return a customized orderby for events.
        """

    def eventResultFields(self):
        """
        Return a customized list of result fields for this object.
        """

    def eventHistoryWhere(self):
        """
        Return a where clause that will find history events for this object.
        """

    def eventHistoryOrderby(self):
        """
        Return a customized orderby for history events.
        """
