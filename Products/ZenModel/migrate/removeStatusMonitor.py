###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__='''
After all the monitors are moved to PerformancConf, remove the Status
Monitor
'''

import Migrate

from Products.ZenRelations.RelSchema import *
from Products.ZenModel.Device import Device


class RemoveStatusMonitor(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        if hasattr(dmd.Monitors, 'StatusMonitors'):
            dmd.Monitors._delObject('StatusMonitors')
        Device._relations = Device._relations + (
            ("monitors", ToMany(ToMany,"Products.ZenModel.StatusMonitorConf","devices")),
            )
        for d in dmd.Devices.getSubDevices():
            if hasattr(d, 'monitors'):
                d._delObject('monitors')
        Device._relations = tuple([x for x in Device._relations if x[0] != 'monitors'])
        try:
            t = dmd.Monitors.rrdTemplates.PerformanceConf.thresholds
            t = t._getOb('zenping cycle time')
            t.maxval = 'here.pingCycleInterval * 0.8'
        except AttributeError, err:
            pass
        for perf in dmd.Monitors.Performance.objectSubValues():
            perf.checkRelations(repair=True)

        # Fix menu items
        dlm = dmd.zenMenus._getOb('Device_list')
        if dlm:
            if dlm.zenMenuItems._getOb('setStatusMonitors', False):
                dlm.zenMenuItems._delObject('setStatusMonitors')

            spm = dlm.zenMenuItems._getOb('setPerformanceMonitor', False)
            if spm:
                spm.description = 'Set Collector...'

        dlm = dmd.zenMenus._getOb('DeviceGrid_list')
        if dlm:
            if dlm.zenMenuItems._getOb('setStatusMonitors_grid', False):
                dlm.zenMenuItems._delObject('setStatusMonitors_grid')

            spm = dlm.zenMenuItems._getOb('setPerformanceMonitor_grid', False)
            if spm:
                spm.description = 'Set Collector...'

        if dmd.zenMenus._getOb('StatusMonitor_list', False):
            dmd.zenMenus._delObject('StatusMonitor_list')

        pml = dmd.zenMenus._getOb('PerformanceMonitor_list')
        if pml:
            apm = pml.zenMenuItems._getOb('addPMonitor', False)
            if apm:
                apm.description = 'Add Collector...'

            rpm = pml.zenMenuItems._getOb('removePMonitors', False)
            if rpm:
                rpm.description = 'Delete Collectors...'

RemoveStatusMonitor()
