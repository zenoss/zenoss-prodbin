##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")


class RemoveEmptyGraphs(Migrate.Step):
    """Remove some graph datapoints from a few services."""

    version = Migrate.Version(108, 0, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        zenmodelers = filter(lambda s: s.name == "zenmodeler", ctx.services)
        log.info("Found %i services named 'zenmodeler'." % len(zenmodelers))
        remove_metrics = ["devices", "eventQueueLength", "timedOut"]
        remove_graphs = ["devices", "eventQueueLength", "timedOut"]
        for zenmodeler in zenmodelers:
            for mc in zenmodeler.monitoringProfile.metricConfigs:
                before = len(mc.metrics)
                mc.metrics = [m for m in mc.metrics if m.ID not in remove_metrics]
                after = len(mc.metrics)
                log.info("Removed %i metrics from zenmodeler." % (before - after))

            before = len(zenmodeler.monitoringProfile.graphConfigs)
            zenmodeler.monitoringProfile.graphConfigs = [
                gc for gc in zenmodeler.monitoringProfile.graphConfigs
                if gc.graphID not in remove_graphs]
            after = len(zenmodeler.monitoringProfile.graphConfigs)
            log.info("Removed %i graphs from zenmodeler." % (before - after))

        # Commit our changes.
        ctx.commit()


RemoveEmptyGraphs()
