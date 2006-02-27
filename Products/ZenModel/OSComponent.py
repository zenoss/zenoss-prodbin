#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

from ManagedEntity import ManagedEntity
from DeviceComponent import DeviceComponent


class OSComponent(DeviceComponent, ManagedEntity):
    """
    Logical Operating System component like a Process, IpInterface, etc.
    """

    def device(self):
        """Return our device object for DeviceResultInt.
        """
        os = self.os()
        if os: return os.device()
