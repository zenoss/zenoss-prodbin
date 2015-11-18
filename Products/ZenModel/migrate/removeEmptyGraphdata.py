##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import re
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration import Command
sm.require("1.0.0")


class RemoveEmptyGraphData(Migrate.Step):
    """Remove some graph datapoints from a few services."""

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zenmodelers = filter(lambda s: s.name == "zenmodeler", ctx.services)
        remove_metrics = ["dataPoints", "eventCount", "missedRuns", "taskCount"]
        remove_graphs = ["dataPoints", "events", "missedRuns", "tasks"]
        for zenmodeler in zenmodelers:
            for mc in zenmodeler.monitoringProfile.metricConfigs:
                mc.metrics = [m for m in mc.metrics if m.ID not in remove_metrics]

            gcs = zenmodeler.monitoringProfile.graphConfigs
            gcs = [gc for gc in gcs if gc.graphID not in remove_graphs]

        # Commit our changes.
        ctx.commit()


RemoveEmptyGraphData()
