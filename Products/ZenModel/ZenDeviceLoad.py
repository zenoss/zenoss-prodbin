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
SYSTEM_PATH=3
GROUP_PATH=4
MANUFACTURER=5
MODEL=6
LOCATION_PATH=7
CRICKET_MONITOR=8


class ZenDeviceLoad(BasicLoader):
    """
    Load devices into the DMD using file created by ZenDeviceDump.
    """

    def loaderBody(self, line):
        line = line.split(":")
        if len(line) != 9: 
            raise ValueError("Wrong number of values in line")
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
            self.log.info("loaded device %s" % deviceName)
        except DeviceExistsError, e:
            self.log.info(e)


if __name__ == '__main__':
    loader = ZenDeviceLoad()
    loader.loadDatabase()
    print "Device load finished!"
