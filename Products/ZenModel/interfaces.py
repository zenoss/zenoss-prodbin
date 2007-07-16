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

import zope.interface

class IDeviceManager:
    """
    Interface implemented for objects that manage devices, like DeviceOrganizers
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

        
class IReport(zope.interface.Interface):

    def run(dmd, args):
        """Dmd is the DataRoot, args are the REQUEST args, this command
        returns a sequence"""

        
