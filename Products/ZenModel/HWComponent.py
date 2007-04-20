###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Hardware import Hardware
from DeviceComponent import DeviceComponent


class HWComponent(DeviceComponent, Hardware):
    """
    Hardware component of a device such as a HardDisk, CPU, etc.
    """

    def device(self):
        """Return our device object for DeviceResultInt.
        """
        hw = self.hw()
        if hw: return hw.device()

