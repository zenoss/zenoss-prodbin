#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

from InterfaceMap import InterfaceMap
from SysedgeFileSystemMap import SysedgeFileSystemMap
from HRFileSystemMap import HRFileSystemMap
from SysedgeMap import SysedgeMap
from DeviceMap import DeviceMap
from RouteMap import RouteMap
from CiscoMap import CiscoMap
from IpServiceMap import IpServiceMap
from SysedgeDiskMap import SysedgeDiskMap

def initCustomMaps(collector):
    collector.addCustomMap(DeviceMap)
    collector.addCustomMap(InterfaceMap)
    collector.addCustomMap(SysedgeFileSystemMap)
    collector.addCustomMap(HRFileSystemMap)
    collector.addCustomMap(SysedgeMap)
    collector.addCustomMap(RouteMap)
    collector.addCustomMap(IpServiceMap)
    collector.addCustomMap(SysedgeDiskMap)
