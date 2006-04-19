import Migrate

class KillCricket(Migrate.Step):
    version = 20.0

    def cutover(self, dmd):
        from Products.ZenModel.MonitorClass import manage_addMonitorClass
        if not hasattr(dmd.Monitors, 'Performance'):
            manage_addMonitorClass(dmd.Monitors, 'Performance')

        from Products.ZenModel.PerformanceConf import manage_addPerformanceConf
        for c in dmd.Monitors.Cricket.objectValues():
            if not hasattr(dmd.Monitors.Performance, c.id):
                manage_addPerformanceConf(dmd.Monitors.Performance, c.id)
                p = dmd.Monitors.Performance._getOb(c.id)
                p.renderurl = c.cricketurl
                p.renderuser = c.cricketuser
                p.renderpass = c.cricketpass

        for dev in dmd.Devices.getSubDevices():
            dev.buildRelations()
            if hasattr(dev, 'cricket') and dev.cricket.getRelatedId():
                dev.setPerformanceMonitor(dev.cricket.getRelatedId())
        if hasattr(dmd.Monitors.Cricket, 'localhost'):
            dmd.Monitors.Cricket._delObject('localhost')

KillCricket()
