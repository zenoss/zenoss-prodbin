###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

class RemoveWinModelerCycleInterval(Migrate.Step):
    ATTR_NAME = 'winmodelerCycleInterval'
    version = Migrate.Version(2, 5, 70)

    def cutover(self, dmd):
        for name in dmd.Monitors.getPerformanceMonitorNames():
            monitor = dmd.Monitors.getPerformanceMonitor(name)
            if hasattr(monitor, RemoveWinModelerCycleInterval.ATTR_NAME):
                delattr(monitor, RemoveWinModelerCycleInterval.ATTR_NAME)

RemoveWinModelerCycleInterval()
