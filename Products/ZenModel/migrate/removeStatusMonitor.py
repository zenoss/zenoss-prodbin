
__doc__='''
After all the monitors are moved to PerformancConf, remove the Status
Monitor
'''

import Migrate

class RemoveStatusMonitor(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def cutover(self, dmd):
        if hasattr(dmd.Monitors, 'StatusMonitors'):
            dmd.Monitors._delObject('StatusMonitors')
        try:
            t = dmd.Monitors.rrdTemplates.PerformanceConf.thresholds
            t = t._getOb('zenping cycle time')
            t.maxval = 'here.pingCycleInterval * 0.8'
        except AttributeError, err:
            pass

RemoveStatusMonitor()
