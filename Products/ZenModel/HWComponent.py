#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

from Hardware import Hardware
from DeviceComponent import DeviceComponent


class HWComponent(Hardware, DeviceComponent):
    """
    Hardware component of a device such as a HardDisk, CPU, etc.
    """

    def device(self):
        """Return our device object for DeviceResultInt.
        """
        hw = self.hw()
        if hw: return hw.device()
