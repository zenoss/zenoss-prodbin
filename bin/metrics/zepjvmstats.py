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

log = logging.getLogger('zenoss.zepjvmmetrics')
logging.basicConfig()
log.setLevel(logging.INFO)


class ZepJvmMetrics(ServiceMetrics):

    def build_gatherer(self):
        return ZepJvmMetricGatherer()


class ZepJvmMetricGatherer(MetricGatherer):

    # Specific URL for zeneventserver
    JVM_STATS_URL = 'http://localhost:8084/zeneventserver/metrics/metrics'

    def __init__(self, interval=30):
        super(ZepJvmMetricGatherer, self).__init__()
        self.interval = interval
        self.prefix = 'zenoss'

    def _extract_data(self, metricdata, timestamp):
        metrics = []

        if 'gauges' in metricdata:
            metrics.extend(self._extract_sub_data(metricdata['gauges'], ['jvm.memory.heap.committed', 'jvm.memory.heap.init','jvm.memory.heap.max','jvm.memory.heap.usage','jvm.memory.heap.used']))
             
        return metrics

    """
    data - container of dictionaries of solr data
    dict_names - list of dictionaries to pull from the container
    """
    def _extract_sub_data(self, data, dict_names):
        metrics = []
        tags = {'internal': 'true'}
        timestamp = time.time()
        for dn in dict_names:
           metric_name = '%s.%s' % (self.prefix, dn)
           metric_value = data.get(dn).get('value')
           log.debug("Adding metric '%s': '%s'", metric_name, metric_value)
           metrics.append(self.build_metric(metric_name, metric_value,timestamp, tags))

        return metrics

    def get_metrics(self):
        metrics = []
        s = requests.Session()
        result = s.get(self.JVM_STATS_URL)
        if result.status_code == 200:
            data = result.json()
            now = time.time()
            log.debug("ZEP JVM stats : %s", json.dumps(data, indent=2, sort_keys=True))
            metrics.extend(self._extract_data(data, now))
        else:
            log.warning("stats request failed for ZEP jvm: %d, %s",
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

        zepjvmm = ZepJvmMetrics(options=args)
        gatherer = zepjvmm.build_gatherer()
        metrics = gatherer.get_metrics()
        pprint(metrics)
    else:
        zepjvmm = ZepJvmMetrics(options=args)
        zepjvmm.run()
