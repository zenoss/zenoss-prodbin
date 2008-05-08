###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import Migrate

class RemoveWinModelerGraphPoints(Migrate.Step):
    version = Migrate.Version(2, 2, 0)

    def balete(self, dmd, path):
        parts = path.split('/')
        obj = dmd
        for part in parts[:-1]:
            obj = obj._getOb(part)
        obj._delObject(parts[-1])

    def cutover(self, dmd):
        base = 'Monitors/rrdTemplates/PerformanceConf/'
        paths = [
            base + 'graphDefs/Cycle Times/graphPoints/zenwinmodeler',
            base + 'thresholds/zenwinmodeler cycle time',
            base + 'datasources/zenwinmodeler',
            ]
        for path in paths:
            try:
                self.balete(dmd, path)
            except AttributeError:
                pass
            

RemoveWinModelerGraphPoints()
