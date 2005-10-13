#################################################################
#
#   Copyright (c) 2005 Zentinel Systems. All rights reserved.
#
#################################################################

__doc__="""CVDeviceUpload

Upload devices from a file with format:
fqdn:prodState:pingStatus:snmpStatus:system:manufacturer:model:location:cricket

$Id: CVServerBackup.py,v 1.1.1.1 2004/10/14 20:55:29 edahl Exp $"""

__version__ = "$Revision: 1.1.1.1 $"[11:-2]

import os

import Globals

from Products.ZenUtils.BasicLoader import BasicLoader
from Products.ZenModel.Device import manage_createDevice
from Products.ZenModel.Exceptions import DeviceExistsError

DEVICE_NAME=0
DEVICE_CLASS=1
PRODUCTION_STATE=2
PING_STATUS=3
SNMP_STATUS=4
SYSTEM_PATH=5
GROUP_PATH=6
MANUFACTURER=7
MODEL=8
LOCATION_PATH=9
CRICKET_MONITOR=10


class ZenDeviceLoad(BasicLoader):
    """
    Load devices into the DMD using file created by ZenDeviceDump.
    """

    def loaderBody(self, line):
        line = line.split(":")
        if len(line) != 11: raise ValueError("Wrong number of values in line")
        deviceName = line[DEVICE_NAME]
        try:
            dev = manage_createDevice(self.dmd, deviceName,
                                    line[DEVICE_CLASS],
                                    productionState=line[PRODUCTION_STATE],
                                    manufacturer=line[MANUFACTURER],
                                    model=line[MODEL],
                                    systemPaths=line[SYSTEM_PATH].split("|"),
                                    groupPaths=line[GROUP_PATH].split("|"),
                                    locationPath=line[LOCATION_PATH],
                                    cricketMonitor=line[CRICKET_MONITOR],
                                    )
            dev.setPingStatus(int(line[PING_STATUS]))
            dev.setSnmpStatus(int(line[SNMP_STATUS]))
            self.log.info("loaded device %s" % deviceName)
        except DeviceExistsError:
            self.log.warn("device %s already exists" % deviceName)


if __name__ == '__main__':
    loader = ZenDeviceLoad()
    loader.loadDatabase()
    print "Device load finished!"
