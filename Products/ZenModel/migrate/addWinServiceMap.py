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
import Migrate
from Acquisition import aq_base

class addWinServiceMap(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        try:
            win = dmd.Devices.getOrganizer("/Server/Windows")
            if not hasattr(aq_base(win),'zCollectorPlugins'):
                win._setProperty("zCollectorPlugins", 
                    (
                        'zenoss.snmp.NewDeviceMap',
                        'zenoss.snmp.DeviceMap',
                        'zenoss.snmp.DellDeviceMap',
                        'zenoss.snmp.HPDeviceMap',
                        'zenoss.snmp.InterfaceMap',
                        'zenoss.snmp.RouteMap',
                        'zenoss.snmp.IpServiceMap',
                        'zenoss.snmp.HRFileSystemMap',
                        'zenoss.snmp.HRSWInstalledMap',
                        'zenoss.snmp.HRSWRunMap',
                        'zenoss.snmp.CpuMap',
                        'zenoss.snmp.DellCPUMap',
                        'zenoss.snmp.DellPCIMap',
                        'zenoss.snmp.HPCPUMap',
                        'zenoss.snmp.InformantHardDiskMap',
                        'zenwin.wmi.WinServiceMap'
                    ), type = 'lines')
            else:
                win.zCollectorPlugins += ('zenwin.wmi.WinServiceMap',)
        except: pass

addWinServiceMap()
 






