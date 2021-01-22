#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import argparse
import json
import logging
import requests
import time

from gather import ServiceMetrics, MetricGatherer

log = logging.getLogger("zenoss.solrmetrics")
logging.basicConfig()
log.setLevel(logging.INFO)


SOLR_STATS_URL = "http://localhost:8983/solr/admin/metrics?wt=json"
SOLR_STATUS_URL = "http://localhost:8983/solr/admin/cores?action=STATUS"
COLLECTION_NAME = "zenoss_model"


class SolrMetrics(ServiceMetrics):

    def build_gatherer(self):
        return SolrMetricGatherer()


class SolrMetricGatherer(MetricGatherer):

    def __init__(self, interval=30):
        super(SolrMetricGatherer, self).__init__()
        self.core_name = ""
        self.interval = interval
        self.prefix = "zenoss.solr"
        self.core_value_metrics = ["INDEX.sizeInBytes"]
        self.core_counter_metrics = [
            "QUERY./select.timeouts",
            "QUERY./select.serverErrors",
            "UPDATE.updateHandler.commits",
            "UPDATE.updateHandler.cumulativeAdds",
            "UPDATE./update/json.serverErrors",
            "UPDATE./update/json.timeouts",
        ]
        self.core_timer_metrics = [
            "QUERY./%s.requestTimes" % action
            for action in ["get", "query", "select"]
        ]
        self.core_timer_metrics.append("UPDATE./update/json.requestTimes")
        self.jvm_value_metrics = [
            "memory.heap.used",
            "memory.total.used",
            "threads.deadlock.count",
            "threads.blocked.count",
            "threads.daemon.count",
            "threads.count",
        ]

    def _extract_metrics(self, data, timestamp):
        metrics = []
        metrics.extend(self._extract_core_metrics(data))
        metrics.extend(self._extract_jvm_metrics(data))
        return metrics

    def _extract_core_metrics(self, data):
        solr_core = next(
            (
                v
                for v in data.values()
                if v.get("CORE.coreName") == self.core_name
            ),
            None,
        )
        if not solr_core:
            return []

        metrics = []
        metrics.extend(
            self._extract_sub_data(
                solr_core, self.core_value_metrics, ["value"]
            )
        )
        metrics.extend(
            self._extract_sub_data(
                solr_core,
                self.core_counter_metrics,
                ["count", "meanRate", "1minRate", "5minRate", "15minRate"],
            )
        )
        metrics.extend(
            self._extract_sub_data(
                solr_core,
                self.core_timer_metrics,
                [
                    "count",
                    "meanRate",
                    "1minRate",
                    "5minRate",
                    "15minRate",
                    "mean_ms",
                    "stddev_ms",
                    "p75_ms",
                    "p95_ms",
                    "p99_ms",
                ],
            )
        )
        return metrics

    def _extract_jvm_metrics(self, data):
        solr_jvm = data.get("solr.jvm")
        return self._extract_sub_data(
            solr_jvm, self.jvm_value_metrics, ["value"]
        )

    """
    data - container of dictionaries of solr data
    dict_names - list of dictionaries to pull from the container
    stat_names - list of stats to get from each dict

    note: strips '/' out of dict names when building metric names from them
    """

    def _extract_sub_data(self, data, dict_names, stat_names):
        metrics = []
        if not data:
            return metrics
        tags = {"internal": "true"}
        timestamp = time.time()
        for dn in dict_names:
            value = data.get(dn)
            for stat in stat_names:
                metric_name = "%s.%s.%s" % (
                    self.prefix,
                    dn.replace("/", ""),
                    stat,
                )
                if isinstance(value, dict):
                    metric_value = value.get(stat)
                else:
                    metric_value = value
                log.debug(
                    "Adding metric '%s': '%s'", metric_name, metric_value
                )
                metrics.append(
                    self.build_metric(
                        metric_name, metric_value, timestamp, tags
                    )
                )
        return metrics

    def get_metrics(self):
        metrics = []
        s = requests.Session()
        if not self.core_name:
            name = self.get_zenoss_model_core_name(s)
            if not name:
                return metrics
            self.core_name = name
        result = s.get(SOLR_STATS_URL)
        if result.status_code == 200:
            data = result.json()
            metric_data = data.get("metrics")
            if not metric_data:
                log.warning("stats request returned no metrics")
            else:
                now = time.time()
                log.debug(
                    "Solr stats : %s",
                    json.dumps(data, indent=2, sort_keys=True),
                )
                metrics.extend(self._extract_metrics(metric_data, now))
        else:
            log.warning(
                "stats request failed for solr: %d, %s",
                result.status_code,
                result.text,
            )
        log.debug(
            "Built metrics: %s" % json.dumps(metrics, indent=2, sort_keys=True)
        )
        return metrics

    def get_zenoss_model_core_name(self, session):
        result = session.get(SOLR_STATUS_URL)
        if result.status_code == 200:
            cores = result.json().get("status")
            for name, val in cores.items():
                if val.get("cloud").get("collection") == COLLECTION_NAME:
                    return name
        else:
            log.warning(
                "couldn't get core for %s collection: %d, %s",
                COLLECTION_NAME,
                result.status_code,
                result.text,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--interval",
        dest="interval",
        type=float,
        default=30,
        help="polling interval in seconds",
    )
    args = parser.parse_args()

    sm = SolrMetrics(options=args)
    sm.run()
