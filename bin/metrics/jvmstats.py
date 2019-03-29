#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import argparse
import json
import logging
import os
import requests
import sys
import time

from pprint import pprint
from gather import ServiceMetrics, MetricGatherer

log = logging.getLogger('zenoss.jvmmetrics')
logging.basicConfig()
log.setLevel(logging.INFO)


class JvmMetrics(ServiceMetrics):

    def build_gatherer(self):
        return JvmMetricGatherer()


class JvmMetricGatherer(MetricGatherer):

    # Generic URL, works for opentsdb reader, opentsdb writer, CetralQuery, MetricConsumer
    JVM_STATS_URL = 'http://localhost:4242/api/stats/jvm'

    def __init__(self, interval=30):
        super(JvmMetricGatherer, self).__init__()
        self.interval = interval
        self.prefix = 'zenoss.jvm'

    def _extract_data(self, metricdata, timestamp):
        metrics = []

        if 'memory' in metricdata:
            data = metricdata['memory']
            metrics.extend(self._extract_sub_data(metricdata['memory'], ['heapMemoryUsage'], ['committed','init','max','used']))

        return metrics

    """
    data - container of dictionaries of solr data
    dict_names - list of dictionaries to pull from the container
    stat_names - list of stats to get from each dict
    """
    def _extract_sub_data(self, data, dict_names, stat_names):
        metrics = []
        tags = {'internal': 'true'}
        timestamp = time.time()
        max=used=''
        for dn in dict_names:
            for stat in stat_names:
                metric_name = '%s.%s.%s' % (self.prefix, dn, stat)
                metric_value = data.get(dn).get(stat)
                if stat == 'used':
                   used = metric_value
                if stat == 'max':
                   max = metric_value
                log.debug("Adding metric '%s': '%s'", metric_name, metric_value)
                metrics.append(self.build_metric(metric_name, metric_value,
                                                 timestamp, tags))

        # Add a metric for usage, calculated from used and max   
        if max != '' and used != '':
           metric_value = str(float(used) / float(max))
           metric_name = '%s.%s.%s' % (self.prefix, dn, 'usage')
           log.debug("Adding metric '%s': '%s'", metric_name, metric_value)
           metrics.append(self.build_metric(metric_name, metric_value,timestamp,tags))

        return metrics

    def get_metrics(self):
        metrics = []
        s = requests.Session()
        result = s.get(self.JVM_STATS_URL)
        if result.status_code == 200:
            data = result.json()
            now = time.time()
            log.debug("JVM stats : %s", json.dumps(data, indent=2, sort_keys=True))
            metrics.extend(self._extract_data(data, now))
        else:
            log.warning("stats request failed for jvm: %d, %s",
                        result.status_code, result.text)
        log.debug("Built metrics: %s" % json.dumps(metrics, indent=2, sort_keys=True))
        return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    parser.add_argument("-v", "--verbose", dest="verbose", action='store_true',
                        help="Run metrics collection once in full debug and dump to stdout.")
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)
        stdout = logging.StreamHandler(sys.stdout)
        log.addHandler(stdout)

        jvmm = JvmMetrics(options=args)
        gatherer = jvmm.build_gatherer()
        metrics = gatherer.get_metrics()
        pprint(metrics)
    else:
        jvmm = JvmMetrics(options=args)
        jvmm.run()
