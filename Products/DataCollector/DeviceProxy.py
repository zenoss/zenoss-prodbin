###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from twisted.spread import pb
class DeviceProxy(pb.Copyable, pb.RemoteCopy):
    """Provide a cache of configuration information as needed by plugins
    while running"""

    def __init__(self):
        pass

    def getSnmpLastCollection(self):
        from DateTime import DateTime
        return DateTime(float(self._snmpLastCollection))

    def getSnmpStatus(self):
        return getattr(self, '_snmpStatus', 0)
    getSnmpStatusNumber = getSnmpStatus

    def getId(self):
        return self.id

pb.setUnjellyableForClass(DeviceProxy, DeviceProxy)
