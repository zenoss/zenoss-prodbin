###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Remove cycleTime datapoint and graphs from collectors since they are no longer tracked.
'''

import Migrate

class RemoveCycleTimeGraph(Migrate.Step):
    version = Migrate.Version(4, 1, 70)

    def cutover(self, dmd):

        template=dmd.Monitors.rrdTemplates.PerformanceConf
        #remove selected graph points from definition if present
        graph = template.graphDefs._getOb('Cycle Times', None)
        if graph:
            graphPoints = ('zenperfsnmp', 'zenping', 'zenstatus')
            graph.manage_deleteGraphPoints(graphPoints)

        #remove threhsolds if present
        thresholdIds = ('zenperfsnmp cycle time', 'zenping cycle time', 'zenprocess cycle time')
        template.manage_deleteRRDThresholds(thresholdIds)

        #remove cycle_time datapoints from all datasources except zenmodeler
        for ds in template.datasources():
            if ds.id != 'zenmodeler' and ds.datapoints._getOb('cycleTime', False):
                ds.manage_deleteRRDDataPoints(['cycleTime'])


RemoveCycleTimeGraph()
