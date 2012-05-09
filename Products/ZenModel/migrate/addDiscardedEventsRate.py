###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__='''

Add data points, a threshold and a graph for tracking each daemon's event queue
length.

'''
import Migrate
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint


class AddDiscardedEventsRate(Migrate.Step):
    version = Migrate.Version(4, 1, 2)

    def cutover(self, dmd):
        template = dmd.Monitors.rrdTemplates._getOb('PerformanceConf', None)
        if not template:
            # No collector performance template exists.
            return

        # Add discardedEvents data point to each data source in the template.
        dsnames = []
        for ds in template.datasources():
            dsnames.append(ds.id)

            if 'discardedEvents' in ds.datapoints.objectIds():
                continue

            newDp = ds.manage_addRRDDataPoint('discardedEvents')
            newDp.rrdtype = 'DERIVE'
            newDp.rrdmin = 0
            newDp.rrdmax = 100000

        dpnames = [ '%s_discardedEvents' % dsname for dsname in dsnames ]

        # Add a Discarded Events graph 
        if 'Discarded Events' not in template.graphDefs.objectIds():
            graph = template.manage_addGraphDefinition('Discarded Events')
            graph.units = 'events / sec'
            graph.miny = 0

            graph.manage_addDataPointGraphPoints(dpnames)

            # Fix up all of the graph points we just added.
            for gp in graph.graphPoints():
                if isinstance(gp, DataPointGraphPoint):
                    gp.format = '%6.0lf'
                    gp.legend = gp.dpName.split('_', 1)[0]

            # Put the Event Queue graph right after Cycle Times
            inserted = False
            for g in template.getGraphDefs():
                if g.id == 'Event Queue':
                    graph.sequence = g.sequence + 1
                    inserted = True
                elif g.id != 'Discarded Events' and inserted:
                    g.sequence = g.sequence + 1


AddDiscardedEventsRate()

