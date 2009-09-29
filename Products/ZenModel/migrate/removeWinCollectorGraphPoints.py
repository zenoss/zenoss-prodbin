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
__doc__='''

Remove the cycleTime graph points for zenwin and zeneventlog since they no
longer apply to daemons using the new ZenCollector framework.
'''
import Migrate

class RemoveWinCollectorGraphPoints(Migrate.Step):
    version = Migrate.Version(2, 5, 0)

    def deleteLastObjectOnPath(self, dmd, path):
        parts = path.split('/')
        obj = dmd
        for part in parts[:-1]:
            obj = obj._getOb(part)
        if obj._getOb(parts[-1], False):
            obj._delObject(parts[-1])

    def cutover(self, dmd):
        base = 'Monitors/rrdTemplates/PerformanceConf/'
        paths = [
            base + 'graphDefs/Cycle Times/graphPoints/zeneventlog',
            base + 'thresholds/zeneventlog cycle time',
            base + 'datasources/zeneventlog/datapoints/cycleTime',
            base + 'graphDefs/Cycle Times/graphPoints/zenwin',
            base + 'thresholds/zenwin cycle time',
            base + 'datasources/zenwin/datapoints/cycleTime',
            ]
        for path in paths:
            try:
                self.deleteLastObjectOnPath(dmd, path)
            except AttributeError:
                pass

RemoveWinCollectorGraphPoints()
