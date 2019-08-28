##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import logging

log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
from servicemigration.metrics import Metric
from servicemigration.graphrange import GraphRange
from servicemigration.graphconfig import GraphConfig
from servicemigration.metricconfig import MetricConfig
from servicemigration.graphdatapoint import GraphDatapoint


sm.require("1.1.12")


class AddZingConfigToZep(Migrate.Step):
    "Add reasonable defaults to zeneventserver to enable sending events to Zenoss cloud"

    version = Migrate.Version(300, 0, 12)

    CLOUD_CONFIG_BLOCK = """

## Configuration to forward events to Zenoss Cloud
#
zep.zing.enabled=false
zep.zing.project={{getContext . "cse.project"}}
zep.zing.tenant={{getContext . "cse.tenant"}}
zep.zing.source={{getContext . "cse.source"}}
zep.zing.topic=event-in
zep.zing.minimum_severity=INFO

# Path to the credentials file in case a svc account key is needed
#zep.zing.credentials=
"""

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        log.info("Starting migration for zeneventserver.conf")

        do_commit = False
        zep = filter(lambda s: s.name == "zeneventserver", ctx.services)[0]
        config_files = zep.originalConfigs + zep.configFiles
        cfgs = filter(lambda f: f.name == "/opt/zenoss/etc/zeneventserver.conf", config_files)

        # add settings to config files
        for cfg in cfgs:
            if "zep.zing.enabled" not in cfg.content:
                log.info("adding cloud-integration config to zeneventserver.conf")
                cfg.content += self.CLOUD_CONFIG_BLOCK
                do_commit = True

        # add graphs for Zenoss cloud integration
        gcs = zep.monitoringProfile.graphConfigs
        mcs = zep.monitoringProfile.metricConfigs

        if not filter(lambda x: x.graphID == 'cloudEventsBytes', gcs):
            log.info("No cloudEventsBytes graph found; creating.")
            do_commit = True
            gcs.extend(
                [
                    GraphConfig(
                        graphID='cloudEventsBytes',
                        name='Bytes published to Pub/Sub',
                        footer=False,
                        returnset='EXACT',
                        graphType='line',
                        miny=0,
                        base=0,
                        yAxisLabel='Bytes Published',
                        description='Bytes published to Pub/Sub',
                        graphRange=GraphRange(
                            start='1h-ago',
                            end='0s-ago'
                        ),
                        datapoints=[
                            GraphDatapoint(
                                aggregator='avg',
                                color="",
                                dataFormat="",
                                fill=False,
                                pointID="bytes",
                                legend="bytes",
                                metric="zeneventserver.zing.bytesSent.count",
                                metricSource="events-to-pubsub",
                                name="bytes",
                                rate=True,
                                rateOptions={
                                    'counter': True
                                },
                                pointType="line"
                            )
                        ]
                    ),
                    GraphConfig(
                        description="Number of events published to Pub/Sub.",
                        footer=False,
                        graphID="eventsPublished",
                        name="Events Published to Pub/Sub",
                        graphRange=GraphRange(
                            end="0s-ago",
                            start="1h-ago"
                        ),
                        returnset="EXACT",
                        graphType="line",
                        miny=0,
                        base=0,
                        yAxisLabel="Events Published",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="avg",
                                color="",
                                dataFormat="",
                                fill=False,
                                pointID="published",
                                legend="published",
                                metric="zeneventserver.zing.sentEvents.count",
                                metricSource="events-to-pubsub",
                                name="published",
                                rate=True,
                                rateOptions={
                                    "counter": True
                                },
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="avg",
                                color="",
                                dataFormat="",
                                fill=False,
                                pointID="failed",
                                legend="failed",
                                metric="zeneventserver.zing.failedEvents.count",
                                metricSource="events-to-pubsub",
                                name="failed",
                                rate=True,
                                rateOptions={
                                    "counter": True
                                },
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="avg",
                                color="",
                                dataFormat="",
                                fill=False,
                                pointID="invalid",
                                legend="invalid",
                                metric="zeneventserver.zing.invalidEvents.count",
                                metricSource="events-to-pubsub",
                                name="invalid",
                                rate=True,
                                rateOptions={
                                    "counter": True
                                },
                                pointType="line"
                            )
                        ]
                    ),
                    GraphConfig(
                        description="Seconds to Forward events to Pub/Sub.",
                        footer=False,
                        builtin=False,
                        graphFormat="",
                        miny=0,
                        base=0,
                        graphID="processEventSeconds",
                        name="Events to Pub/Sub Time (seconds)",
                        graphRange=GraphRange(
                            end="0s-ago",
                            start="1h-ago"
                        ),
                        returnset="EXACT",
                        graphType="line",
                        yAxisLabel="Events to Pub/Sub Time (s)",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="avg",
                                color="",
                                dataFormat="",
                                fill=False,
                                pointID="min",
                                legend="min",
                                metric="zeneventserver.zing.processEvent.min",
                                metricSource="events-to-pubsub",
                                name="min",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="avg",
                                color="",
                                dataFormat="",
                                fill=False,
                                pointID="max",
                                legend="max",
                                metric="zeneventserver.zing.processEvent.max",
                                metricSource="events-to-pubsub",
                                name="max",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="avg",
                                color="",
                                dataFormat="",
                                fill=False,
                                pointID="mean",
                                legend="mean",
                                metric="zeneventserver.zing.processEvent.mean",
                                metricSource="events-to-pubsub",
                                name="mean",
                                rate=False,
                                pointType="line"
                            )
                        ]
                    )
                ]
            )

            if not filter(lambda x: x.ID == 'events-to-pubsub', mcs):
                log.info("No events-to-pubsub metric config found; creating it and others.")
                do_commit = True
                mcs.append(
                    MetricConfig(
                        ID="events-to-pubsub",
                        description="Statistics for outgoing events to Pub/Sub",
                        name="Events to Pub/Sub",
                        metrics=[
                            Metric(
                                ID="zeneventserver.zing.bytesSent.count",
                                name="bytes",
                                description="number of event bytes sent",
                                counter=True,
                                unit="bytes"
                            ),
                            Metric(
                                ID="zeneventserver.zing.failedEvents.count",
                                name="failedEvents",
                                description="number of events failed when publishing to Pub/Sub",
                                counter=True,
                                unit="events"
                            ),
                            Metric(
                                ID="zeneventserver.zing.invalidEvents.count",
                                name="invalidEvents",
                                description="number of invalid events that were not sent to Pub/Sub",
                                counter=True,
                                unit="events"
                            ),
                            Metric(
                                ID="zeneventserver.zing.irrelevantSeverityEvents.count",
                                name="irrelevantSeverityEvents",
                                description="number of events dropped for not meeting minimum severity criteria",
                                counter=True,
                                unit="events"
                            ),
                            Metric(
                                ID="zeneventserver.zing.sentEvents.count",
                                name="sentEvents",
                                description="number of events successfully sent to Pub/Sub",
                                counter=True,
                                unit="events"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.count",
                                name="count",
                                description="number of calls to processEvent",
                                counter=True,
                                unit="events"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.max",
                                name="max",
                                description="max time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.mean",
                                name="mean",
                                description="mean time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.min",
                                name="min",
                                description="min time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.p50",
                                name="p50",
                                description="50th percentile time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.p75",
                                name="p75",
                                description="75th percentile time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.p95",
                                name="p95",
                                description="95th percentile time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.p98",
                                name="p98",
                                description="98th percentile time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.p99",
                                name="p99",
                                description="99th percentile time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.p999",
                                name="p99.9",
                                description="99.9th percentile time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.stddev",
                                name="stddev",
                                description="stddev time in processEvent",
                                counter=False,
                                unit="seconds"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.m15_rate",
                                name="15MinuteRate",
                                description="15 minute processEvent rate",
                                counter=False,
                                unit="evt/sec"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.m1_rate",
                                name="1MinuteRate",
                                description="1 minute processEvent rate",
                                counter=False,
                                unit="evt/sec"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.m5_rate",
                                name="5MinuteRate",
                                description="5 minute processEvent rate",
                                counter=False,
                                unit="evt/sec"
                            ),
                            Metric(
                                ID="zeneventserver.zing.processEvent.mean_rate",
                                name="meanRate",
                                description="mean processEvent rate",
                                counter=False,
                                unit="evt/sec"
                            )
                        ]
                    )
                )

        # Commit our changes.
        if do_commit:
            ctx.commit()


AddZingConfigToZep()
