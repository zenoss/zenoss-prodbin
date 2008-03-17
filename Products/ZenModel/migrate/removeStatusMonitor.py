
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

RemoveStatusMonitor()
