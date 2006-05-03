#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Change the Cricket relationship in Devices to Performance
to reflect the change from Cricket to zenperfsnmp performance
monitoring.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from Acquisition import aq_base

import Migrate

class KillCricket(Migrate.Step):
    version = 20.0

    def convert(self, dc):
        """Convert DeviceClass objects.
        """
        dc.buildRelations()
        if hasattr(aq_base(dc), "zCricketDeviceType"):
            dc._delProperty("zCricketDeviceType")
        if hasattr(aq_base(dc), "zCricketInterfaceIgnoreNames"):
            dc._delProperty("zCricketInterfaceIgnoreNames")
        if hasattr(aq_base(dc), "zCricketInterfaceIgnoreTypes"):
            dc._delProperty("zCricketInterfaceIgnoreTypes")
        if hasattr(aq_base(dc), "zCricketInterfaceMap"):
            dc._delProperty("zCricketInterfaceMap")


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
            if hasattr(dev, '_snmpUpTime'):
                delattr(dev, '_snmpUpTime')
            for fs in dev.os.filesystems():
                if not callable(fs.totalBytes):
                    delattr(fs, 'totalBytes')
                if not callable(fs.usedBytes):
                    delattr(fs, 'usedBytes')
                if not callable(fs.availBytes):
                    delattr(fs, 'availBytes')
                if not callable(fs.availFiles):
                    delattr(fs, 'availFiles')
                if not callable(fs.capacity):
                    delattr(fs, 'capacity')
                if not callable(fs.inodeCapacity):
                    delattr(fs, 'inodeCapacity')

        if hasattr(dmd.Monitors.Cricket, 'localhost'):
            dmd.Monitors.Cricket._delObject('localhost')
        
        for dc in dmd.Devices.getSubOrganizers():
            self.convert(dc)
        self.convert(dmd.Devices)

KillCricket()
