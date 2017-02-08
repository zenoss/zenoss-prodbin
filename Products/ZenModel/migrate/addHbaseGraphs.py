##############################################################################
#
# Copyright (C) Zenoss, Inc. 2016, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import Migrate
import logging
import servicemigration as sm
import os
from servicemigration.graphconfig import GraphConfig
from servicemigration.graphrange import GraphRange
from servicemigration.graphdatapoint import GraphDatapoint
from servicemigration.configfile import ConfigFile

sm.require("1.0.0")
log = logging.getLogger("zen.migrate")


class AddHbaseGraphs(Migrate.Step):
    """
        Adds Graphs that show HBase metrics
    """

    version = Migrate.Version(5, 2, 0)

    def cutover(self, dmd):

        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        hmaster = filter(lambda s: s.name == "HMaster", ctx.services)
        region_server = filter(lambda s: s.name == "RegionServer", ctx.services)

        updatedContext = False

        for service in hmaster:
            configs = service.originalConfigs

            if not filter(lambda x: x.name == "/opt/hbase/conf/hadoop-metrics2-hbase.properties", configs):
                updatedContext = True
                log.info("Adding hmaster metrics config file")
                configs.append(
                    ConfigFile(
                        filename="/opt/hbase/conf/hadoop-metrics2-hbase.properties",
                        name="/opt/hbase/conf/hadoop-metrics2-hbase.properties",
                        content=open(os.path.join(os.path.dirname(__file__), "config-files", "hmaster", "hadoop-metrics2-hbase.properties"), 'r').read()
                    )
                )

            graph_config = service.monitoringProfile.graphConfigs
            if not filter(lambda x: x.graphID == "logStats", graph_config):
                updatedContext = True
                graph_config.append(
                    GraphConfig(
                        graphID="logStats",
                        description="Log Stats",
                        footer=False,
                        miny=0,
                        name="Log Stats",
                        graphRange=GraphRange(start="1h-ago", end="0s-ago"),
                        returnset="EXACT",
                        graphType="line",
                        yAxisLabel="events",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=False,
                                pointID="LogFatal",
                                legend="Total number of fatal log events",
                                metric="LogFatal",
                                name="LogFatal",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=False,
                                pointID="LogError",
                                legend="Total number of error log events",
                                metric="LogError",
                                name="LogError",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=False,
                                pointID="LogWarn",
                                legend="Total number of warn log events",
                                metric="LogWarn",
                                name="LogWarn",
                                rate=False,
                                pointType="line"
                            )
                        ]
                    )
                )
            if not filter(lambda x: x.graphID == "regionServers", graph_config):
                updatedContext = True
                graph_config.append(
                    GraphConfig(
                        graphID="regionServers",
                        description="Region Servers",
                        footer=False,
                        miny=0,
                        name="Region Servers",
                        graphRange=GraphRange(start="10s-ago", end="0s-ago"),
                        returnset="EXACT",
                        graphType="line",
                        yAxisLabel="servers",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="numRegionServers",
                                legend="Total number of live regions servers",
                                metric="numRegionServers",
                                name="numRegionServers",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="numDeadRegionServers",
                                legend="Total number of dead regions servers",
                                metric="numDeadRegionServers",
                                name="numDeadRegionServers",
                                rate=False,
                                pointType="line"
                            )
                        ]
                    )
                )
        for service in region_server:

            configs = service.originalConfigs

            if not filter(lambda x: x.name == "/opt/hbase/conf/hadoop-metrics2-hbase.properties", configs):
                updatedContext = True
                log.info("Adding region server metrics config file")
                configs.append(
                    ConfigFile(
                        filename="/opt/hbase/conf/hadoop-metrics2-hbase.properties",
                        name="/opt/hbase/conf/hadoop-metrics2-hbase.properties",
                        content=open(os.path.join(os.path.dirname(__file__), "config-files", "regionserver", "hadoop-metrics2-hbase.properties"), 'r').read()
                    )
                )

            graph_config = service.monitoringProfile.graphConfigs
            if not filter(lambda x: x.graphID == "QueueLength", graph_config):
                updatedContext = True
                graph_config.append(
                    GraphConfig(
                        graphID="QueueLength",
                        description="Queue Length",
                        footer=False,
                        miny=0,
                        name="Queue Length",
                        graphRange=GraphRange(start="10s-ago", end="0s-ago"),
                        returnset="EXACT",
                        graphType="line",
                        yAxisLabel="Blocks of items",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="numCallsInGeneralQueue",
                                legend="Current depth of the User Requests",
                                metric="numCallsInGeneralQueue",
                                name="numCallsInGeneralQueue",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="numCallsInPriorityQueue",
                                legend="Current depth of the Internal Housekeeping Requests queue",
                                metric="numCallsInPriorityQueue",
                                name="numCallsInPriorityQueue",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="flushQueueLength",
                                legend="Current depth of the memstore flush queue",
                                metric="flushQueueLength",
                                name="flushQueueLength",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="compactionQueueLength",
                                legend="Current depth of the compaction request queue",
                                metric="compactionQueueLength",
                                name="compactionQueueLength",
                                rate=False,
                                pointType="line"
                            )
                        ]
                    )
                )
            if not filter(lambda x: x.graphID == "slowOps", graph_config):
                updatedContext = True
                graph_config.append(
                    GraphConfig(
                        graphID="slowOps",
                        description="Slow Operations",
                        footer=False,
                        miny=0,
                        name="Slow Operations",
                        graphRange=GraphRange(start="10s-ago", end="0s-ago"),
                        returnset="EXACT",
                        graphType="line",
                        yAxisLabel="Operations",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="slowAppendCount",
                                legend="The number of slow append operations",
                                metric="slowAppendCount",
                                name="slowAppendCount",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="slowDeleteCount",
                                legend="The number of slow delete operations",
                                metric="slowDeleteCount",
                                name="slowDeleteCount",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="slowGetCount",
                                legend="The number of slow get operations",
                                metric="slowGetCount",
                                name="slowGetCount",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="slowIncrementCount",
                                legend="The number of slow increment operations",
                                metric="slowIncrementCount",
                                name="slowIncrementCount",
                                rate=False,
                                pointType="line"
                            )
                        ]
                    )
                )
            if not filter(lambda x: x.graphID == "opcounts", graph_config):
                updatedContext = True
                graph_config.append(
                    GraphConfig(
                        graphID="opcounts",
                        description="Operation Counts",
                        footer=False,
                        miny=0,
                        name="Operation Counts",
                        graphRange=GraphRange(start="10s-ago", end="0s-ago"),
                        returnset="EXACT",
                        graphType="line",
                        yAxisLabel="Operations",
                        datapoints=[
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="totalRequestCount",
                                legend="The total number of requests received",
                                metric="totalRequestCount",
                                name="totalRequestCount",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="readRequestCount",
                                legend="The total number of read requests received",
                                metric="readRequestCount",
                                name="readRequestCount",
                                rate=False,
                                pointType="line"
                            ),
                            GraphDatapoint(
                                aggregator="zimsum",
                                fill=True,
                                pointID="writeRequestCount",
                                legend="The total number of write requests received",
                                metric="writeRequestCount",
                                name="writeRequestCount",
                                rate=False,
                                pointType="line"
                            )
                        ]
                    )
                )
        if updatedContext:
            log.info("committing context with Hbase metric updates")
            ctx.commit()


AddHbaseGraphs()
