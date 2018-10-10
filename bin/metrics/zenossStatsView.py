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
        return ZProxyMetricGatherer(interval=self.interval)


class ZProxyMetricGatherer(MetricGatherer):
    # ZPROXY_STATS_URL = 'http://localhost:9080/zport/dmd/zenossStatsView/'
    ZPROXY_STATS_URL = 'http://%s/zport/dmd/zenossStatsView/'
    ZPROXY_CONF_DIR = '/opt/zenoss/zproxy/conf/'
    # Note that changing the follwing ID format will break this script.
    INSTANCE_ID_FORMAT = '{}_{}'

    def __init__(self, interval=30):
        super(ZProxyMetricGatherer, self).__init__()
        self.zopes = self.get_zopes(first_time=True)
        self.interval = interval

    def _extract_data(self, metricdata, timestamp, id_):
        metrics = []
        prefix = 'zenoss.zproxy'
        tags = {'zenoss_zope_instance': id_}
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

    def get_zopes(self, first_time=False):
        if first_time:
            self.zopes = {}

        # Check mtime of /opt/zenoss/zproxy/conf/zope-upstreams.conf
        # if it's newer than, say, now - self.interval, reread it.
        zope_upstream_file = self.ZPROXY_CONF_DIR + 'zope-upstreams.conf'
        zenapi_upstream_file = self.ZPROXY_CONF_DIR + 'apizopes-upstreams.conf'
        zenreports_upstream_file = self.ZPROXY_CONF_DIR + 'zopereports-upstreams.conf'
        zauth_upstream_file = self.ZPROXY_CONF_DIR + 'zauth-upstreams.conf'

        def check_upstream_util(upstream_file):
            upstream_modified = os.path.getmtime(upstream_file)
            now = time.time()
            zopes = []
            if first_time or upstream_modified > (now - self.interval):
                with open(upstream_file, 'r') as inf:
                    zopes = inf.readlines()
                    zopes = [line.rstrip('\n;') for line in zopes]
                    zopes = [line.split(' ')[-1] for line in zopes]
            return zopes

        def check_upstream(svcName, upstream_file):
            instances = check_upstream_util(upstream_file)
            if instances:
                for k in self.zopes.keys():
                    if k.startswith(svcName+'_'):
                        del self.zopes[k]
                for i, instance in enumerate(instances):
                    id_ = self.INSTANCE_ID_FORMAT.format(svcName, i)
                    self.zopes[id_] = instance

        check_upstream('Zope', zope_upstream_file)
        check_upstream('zenapi', zenapi_upstream_file)
        check_upstream('zenreports', zenreports_upstream_file)
        check_upstream('Zauth', zauth_upstream_file)

        return self.zopes

    def get_metrics(self):
        metrics = []
        zopes = self.get_zopes()
        if not zopes:
            return []
        for id_, zope in zopes.iteritems():
            try:
                s = requests.Session()
                result = s.get(self.ZPROXY_STATS_URL % zope)
                if result.status_code == 200:
                    data = result.json()
                    now = time.time()
                    log.debug("Got stats info for zope %i: %s", id_,
                              json.dumps(data, indent=2, sort_keys=True))
                    metrics.extend(self._extract_data(data, now, id_))
                else:
                    log.warning("ZProxy stats request failed for %s: %d, %s",
                                id_, result.status_code, result.text)
            except Exception as e:
                log.error("Error getting %s stats: %s", id_, e.message)
        log.debug("Built metrics: %s" % json.dumps(metrics, indent=2, sort_keys=True))
        log.info("Gathered %i metrics", len(metrics))
        return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    args = parser.parse_args()

    zpm = ZProxyMetrics(options=args)
    zpm.run()
