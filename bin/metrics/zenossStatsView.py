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
import os
import requests
import time
import traceback

from gather import ServiceMetrics, MetricGatherer

log = logging.getLogger('zenoss.zproxymetrics')
logging.basicConfig()
log.setLevel(logging.INFO)


class ZProxyMetrics(ServiceMetrics):

    def build_gatherer(self):
        if self.service == "zproxy":
            return ZProxyMetricGatherer()


class ZProxyMetricGatherer(MetricGatherer):
    # ZPROXY_STATS_URL = 'http://localhost:9080/zport/dmd/zenossStatsView/'
    ZPROXY_STATS_URL = 'http://%s/zport/dmd/zenossStatsView/'

    def __init__(self):
        super(ZProxyMetricGatherer, self).__init__()
        self.zopes = ['localhost:9080']

    def _extract_data(self, metricdata, timestamp, instance=0):
        metrics = []
        prefix = 'zenoss.zproxy'
        tags = {'zope_instance': instance}
        if 'Zope' in metricdata:
            zope_data = metricdata['Zope']
            for name in ["VmData", "VmExe", "VmHWM", "VmLck", "VmLib", "VmPTE",
                         "VmPeak", "VmPin", "VmRSS", "VmSize", "VmStk", "VmSwap",
                         "activeSessions", "freeThreads", "request1m",
                         "requestTimeAvg1m", "requestTotal", "totalThreads",]:
                metric_name = '%s.zope.%s' % (prefix, name)
                metric_value = zope_data.get(name)
                log.debug("Adding metric '%s': '%s'", metric_name, metric_value)
                metrics.append(self.build_metric(metric_name, metric_value,
                                                 timestamp, tags))
        if 'ZODB_main' in metricdata:
            zodb_data = metricdata['ZODB_main']
            for name in ["cacheLength", "cacheSize", "databaseSize",
                         "totalConnections", "totalLoadCount",
                         "totalStoreCount",]:
                metric_name = '%s.zodbmain.%s' % (prefix, name)
                metric_value = zodb_data.get(name)
                log.debug("Adding metric '%s': '%s'", metric_name, metric_value)
                metrics.append(self.build_metric(metric_name, metric_value,
                                                 timestamp, tags))
        if 'ZODB_temp' in metricdata:
            zodb_data = metricdata['ZODB_temp']
            for name in ["cacheLength", "cacheSize", "databaseSize",
                         "totalConnections", "totalLoadCount",
                         "totalStoreCount",]:
                metric_name = '%s.zodbtemp.%s' % (prefix, name)
                metric_value = zodb_data.get(name)
                log.debug("Adding metric '%s': '%s'", metric_name, metric_value)
                metrics.append(self.build_metric(metric_name, metric_value,
                                                 timestamp, tags))
        return metrics

    def get_zopes(self):
        # Check mtime of /opt/zenoss/zproxy/conf/zope-upstreams.conf
        # if it's newer than, say, now - self.interval, reread it.
        upstream_file = '/opt/zenoss/zproxy/conf/zope-upstreams.conf'
        upstream_modified = os.path.getmtime(upstream_file)
        now = time.time()
        if upstream_modified > (now - self.interval):
            with open(upstream_file, 'r') as inf:
                zopes = inf.readlines()
                zopes = [line.rstrip('\n:') for line in zopes]
                zopes = [line.split(' ')[-1] for line in zopes]
                self.zopes = zopes
        return self.zopes


    def get_metrics(self):
        metrics = []
        #zopes = self.get_zopes()
        zopes = ['127.0.0.1:9080']
        if not zopes:
            return []
        for instance, zope in enumerate(zopes):
            s = requests.Session()
            result = s.get(self.ZPROXY_STATS_URL % zope)
            if result.status_code == 200:
                data = result.json()
                now = time.time()
                log.debug("Got stats info for zope %i: %s", instance,
                          json.dumps(data, indent=2, sort_keys=True))
                metrics.extend(self._extract_data(data, now, instance))
            else:
                log.warning("ZProxy stats request failed for zope %i: %d, %s",
                            instance, result.status_code, result.text)
        log.debug("Built metrics: %s" % json.dumps(metrics, indent=2, sort_keys=True))
        return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("service", help="the service for which to collect metrics")
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    args = parser.parse_args()

    sm = ZProxyMetrics(options=args)
    sm.run()
