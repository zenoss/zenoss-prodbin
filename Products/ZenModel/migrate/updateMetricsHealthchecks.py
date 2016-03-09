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
from servicemigration import HealthCheck
sm.require("1.0.0")


class UpdateMetricsHealthChecks(Migrate.Step):
    version = Migrate.Version(5, 2, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # find the target services
        zope_svc = None
        zenhub_svc = None
        zenpy_svc = None
        for s in ctx.services:
            if s.name.lower() == "zope":
                zope_svc = s
            if s.name.lower() == "zenhub":
                zenhub_svc = s
            if s.name.lower() == "zenpython":
                zenpy_svc = s

        # remove intended zproxy_answering or previously added HC
        svcs = [s for s in [zope_svc, zenhub_svc, zenpy_svc] if s is not None]
        for svc in svcs:
            log.info("Processing service:%s.", svc.name)
            for hc in filter(lambda hc:
                             hc.name == "zproxy_answering" or
                             hc.name == "central_query_answering" or
                             hc.name == "metric_consumer_answering",
                             svc.healthChecks):
                svc.healthChecks.remove(hc)
                log.info("Removed healthcheck:%s from service:%s.", hc.name, svc.name)

        # add intended health checks
        query_hc = HealthCheck(name="central_query_answering",
                               interval=10.0,
                               script="/opt/zenoss/bin/healthchecks/query_answering")
        metrics_hc = HealthCheck(name="metric_consumer_answering",
                                 interval=10.0,
                                 script="/opt/zenoss/bin/healthchecks/metrics_answering")

        # adding both to zenpython
        zenpy_svc.healthChecks.append(query_hc)
        log.info("Updated 'central_query_answering' healthcheck for zenpython.")

        # adding central query zenhub
        zenhub_svc.healthChecks.append(query_hc)
        log.info("Updated 'Central_query_answering' healthcheck for zenhub.")
        zenhub_svc.healthChecks.append(metrics_hc)
        log.info("Updated 'metric_consumer_answering' healthcheck for zenhub.")

        ctx.commit()

UpdateMetricsHealthChecks()
