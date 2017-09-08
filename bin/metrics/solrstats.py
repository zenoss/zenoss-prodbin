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

log = logging.getLogger('zenoss.solrmetrics')
logging.basicConfig()
log.setLevel(logging.INFO)


class SolrMetrics(ServiceMetrics):

    def build_gatherer(self):
        return SolrMetricGatherer()


class SolrMetricGatherer(MetricGatherer):

    SOLR_STATS_URL = 'http://localhost:8983/solr/admin/metrics?wt=json'

    def __init__(self, interval=30):
        super(SolrMetricGatherer, self).__init__()
        self.interval = interval
        self.prefix = 'zenoss.solr'
        self.core_value_metrics = ["INDEX.sizeInBytes"]
        self.core_counter_metrics = ["QUERY./select.timeouts", "QUERY./select.serverErrors",
                                     "UPDATE.updateHandler.commits", "UPDATE.updateHandler.cumulativeAdds",
                                     "UPDATE./update/json.serverErrors", "UPDATE./update/json.timeouts"]
        self.core_timer_metrics = ["QUERY./%s.requestTimes" % action for action in ['get', 'query', 'select']]
        self.core_timer_metrics.append("UPDATE./update/json.requestTimes")
        self.jvm_value_metrics = ['memory.heap.used', 'memory.total.used', 'threads.deadlock.count',
                                  'threads.blocked.count', 'threads.daemon.count', 'threads.count']

    def _extract_data(self, metricdata, timestamp):
        metrics = []

        if 'metrics' in metricdata:
            data = metricdata['metrics']
            # the solr metric data is shaped strangely: [string, dict, string, dict], etc,
            # where each string is a label for its subsequent dictionary of metrics.
            # these core metrics live at index 1, following the 1st label
            solr_core = data[1]
            metrics.extend(self._extract_sub_data(solr_core, self.core_value_metrics, ['value']))
            metrics.extend(self._extract_sub_data(solr_core, self.core_counter_metrics, ['count', 'meanRate',
                                                                                         '1minRate','5minRate',
                                                                                         '15minRate']))
            metrics.extend(self._extract_sub_data(solr_core, self.core_timer_metrics, ['count', 'meanRate', '1minRate',
                                                                                       '5minRate', '15minRate',
                                                                                       'mean_ms', 'stddev_ms',
                                                                                       'p75_ms', 'p95_ms', 'p99_ms']))

            # jvm data
            solr_jvm = data[5]
            metrics.extend(self._extract_sub_data(solr_jvm, self.jvm_value_metrics, ['value']))

        return metrics

    """
    data - container of dictionaries of solr data
    dict_names - list of dictionaries to pull from the container
    stat_names - list of stats to get from each dict
    
    note: strips '/' out of dict names when building metric names from them
    """
    def _extract_sub_data(self, data, dict_names, stat_names):
        metrics = []
        tags = {'internal': 'true'}
        timestamp = time.time()
        for dn in dict_names:
            for stat in stat_names:
                metric_name = '%s.%s.%s' % (self.prefix, dn.replace('/', ''), stat)
                metric_value = data.get(dn).get(stat)
                log.debug("Adding metric '%s': '%s'", metric_name, metric_value)
                metrics.append(self.build_metric(metric_name, metric_value,
                                                 timestamp, tags))
        return metrics

    def get_metrics(self):
        metrics = []
        s = requests.Session()
        result = s.get(self.SOLR_STATS_URL)
        if result.status_code == 200:
            data = result.json()
            now = time.time()
            log.debug("Solr stats : %s", json.dumps(data, indent=2, sort_keys=True))
            metrics.extend(self._extract_data(data, now))
        else:
            log.warning("stats request failed for solr: %d, %s",
                        result.status_code, result.text)
        log.debug("Built metrics: %s" % json.dumps(metrics, indent=2, sort_keys=True))
        return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    args = parser.parse_args()

    sm = SolrMetrics(options=args)
    sm.run()
