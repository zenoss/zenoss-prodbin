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
from Products.ZenModel.DeviceClass import DeviceClass

class zCollectorPlugins(Migrate.Step):
    version = Migrate.Version(1, 2, 0)

    clist = (
        'zenoss.snmp.NewDeviceMap',
        'zenoss.snmp.DeviceMap',
        'zenoss.snmp.InterfaceMap',
        'zenoss.snmp.RouteMap',
    )

    def cutover(self, dmd):
        if not hasattr(aq_base(dmd.Devices), 'zCollectorPlugins'):
            dmd.Devices._setProperty("zCollectorPlugins", clist, type='lines')
        if not dmd.Devices.zCollectorPlugins:
            dmd.Devices.zCollectorPlugins = (
                    'zenoss.snmp.NewDeviceMap',
                    'zenoss.snmp.DeviceMap',
                    'zenoss.snmp.InterfaceMap',
                    'zenoss.snmp.RouteMap',
                )
        if not dmd.Devices.Server.zCollectorPlugins:
            dmd.Devices.Server.zCollectorPlugins = (
                    'zenoss.snmp.NewDeviceMap',
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
                )

        if not aq_base(hasattr(dmd.Devices.Server,'Scan')):
            scan = DeviceClass('Scan')
            dmd.Devices.Server._setObject('Scan',scan)

        if not dmd.Devices.Server.Scan.zCollectorPlugins:
            dmd.Devices.Server.Scan.zCollectorPlugins = (
                    'zenoss.portscan.IpServiceMap',
                )
        
        if not aq_base(hasattr(dmd.Devices.Server,'Cmd')):
            cmd = DeviceClass('Cmd')
            dmd.Devices.Server._setObject('Cmd', cmd)

        if not dmd.Devices.Server.Cmd._getOb('zCollectorPlugins',False):
            dmd.Devices.Server.Cmd.zCollectorPlugins = (
                    'zenoss.cmd.uname',
                    'zenoss.cmd.df',
                    'zenoss.cmd.linux.ifconfig',
                    'zenoss.cmd.linux.memory',
                    'zenoss.cmd.linux.netstat_an',
                    'zenoss.cmd.linux.netstat_rn',
                    'zenoss.cmd.linux.process',
                    'zenoss.cmd.darwin.cpu',
                    'zenoss.cmd.darwin.ifconfig',
                    'zenoss.cmd.darwin.memory',
                    'zenoss.cmd.darwin.netstat_an',
                    'zenoss.cmd.darwin.process',
                    'zenoss.cmd.darwin.swap',
                )


        if not dmd.Devices.Server.Linux._getOb('zCollectorPlugins',False):
            dmd.Devices.Server.Linux.zCollectorPlugins = (
                    'zenoss.snmp.NewDeviceMap',
                    'zenoss.snmp.DeviceMap',
                    'zenoss.snmp.DellDeviceMap',
                    'zenoss.snmp.HPDeviceMap',
                    'zenoss.snmp.InterfaceMap',
                    'zenoss.snmp.RouteMap',
                    'zenoss.snmp.IpServiceMap',
                    'zenoss.snmp.HRFileSystemMap',
                    'zenoss.snmp.HRSWRunMap',
                    'zenoss.snmp.CpuMap',
                    'zenoss.snmp.DellCPUMap',
                    'zenoss.snmp.DellPCIMap',
                    'zenoss.snmp.HPCPUMap',
                )

        if not dmd.Devices.Server.Windows._getOb('zCollectorPlugins',False):
            dmd.Devices.Server.Windows.zCollectorPlugins = (
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
                )
            
        if not dmd.Devices.Power._getOb('zCollectorPlugins',False):
            dmd.Devices.Power.zCollectorPlugins = (
                    'zenoss.snmp.NewDeviceMap',
                    'zenoss.snmp.DeviceMap',
                    'zenoss.snmp.APCDeviceMap',
                    'zenoss.snmp.PowerwareDeviceMap',
                )
        
        if not dmd.Devices.Network._getOb('zCollectorPlugins',False):
            dmd.Devices.Network.Router.zCollectorPlugins = (
                    'zenoss.snmp.NewDeviceMap',
                    'zenoss.snmp.DeviceMap',
                    'zenoss.snmp.InterfaceMap',
                    'zenoss.snmp.RouteMap',
                )

        if not dmd.Devices.Network.Router.Cisco._getOb(
            'zCollectorPlugins',False):
            dmd.Devices.Network.Router.Cisco.zCollectorPlugins = (
                    'zenoss.snmp.NewDeviceMap',
                    'zenoss.snmp.DeviceMap',
                    'zenoss.snmp.CiscoMap',
                    'zenoss.snmp.InterfaceMap',
                    'zenoss.snmp.CiscoHSRP',
                    'zenoss.snmp.RouteMap',
                )

zCollectorPlugins()
 






