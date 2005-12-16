#################################################################
#
#   Copyright (c) 2002 Zentinel Systems, Inc. All rights reserved.
#
#################################################################

from Hardware import Hardware
from DeviceComponent import DeviceComponent


class HWComponent(Hardware, DeviceComponent):
    """
    Hardware component of a device such as a HardDisk, CPU, etc.
    """
