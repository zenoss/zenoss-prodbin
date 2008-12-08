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

__doc__ = """DeviceProxy
Memoxing object for SNMP-collecting devices
"""

from twisted.spread import pb
class DeviceProxy(pb.Copyable, pb.RemoteCopy):
    """
    Provide a cache of configuration information as needed by plugins
    while running
    """

    def __init__(self):
        """
        Do not use base classes intializers
        """
        pass


    def getSnmpLastCollection(self):
        """
        Return the time of the last collection time

        @return: time of the last collection
        @rtype: Python DateTime object
        """
        from DateTime import DateTime
        return DateTime(float(self._snmpLastCollection))


    def getSnmpStatus(self):
        """
        Numeric status of our SNMP collection

        @return: status
        @rtype: number
        """
        return getattr(self, '_snmpStatus', 0)
    getSnmpStatusNumber = getSnmpStatus


    def getId(self):
        """
        Return our id        

        @return: identification
        @rtype: string
        """
        return self.id

pb.setUnjellyableForClass(DeviceProxy, DeviceProxy)
