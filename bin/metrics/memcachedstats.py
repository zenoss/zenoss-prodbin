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
import logging
import os
import re
import socket
import sys
import time

from pprint import pprint
from gather import ServiceMetrics, MetricGatherer

log = logging.getLogger('zenoss.memcachedmetrics')
logging.basicConfig()
log.setLevel(logging.INFO)


class MemcachedMetrics(ServiceMetrics):
    def __init__(self, options):
        super(MemcachedMetrics, self).__init__(options)
        self.interval = options.interval

    def build_gatherer(self):
        return MemcachedMetricGatherer(self.interval)


class MemcachedMetricGatherer(MetricGatherer):

    HOST = 'localhost'
    PORT = 11211

    def __init__(self, interval):
        self.interval = interval
        self.prefix = 'zenoss.memcached.'
        # Get Control Plane ID
        self.service_id = os.environ.get('CONTROLPLANE_SERVICED_ID', '')

    def _extract_data(self, data):
        metrics = []
        tags = {'controlplane_service_id': self.service_id}
        timestamp = time.time()
        r = re.compile(r"\bSTAT\b\s(\w*)\s[+-]?([0-9]*[.]?[0-9]+)$")

        results = data.split('\r\n')

        for result in results:
            if r.match(result):
                metric_name = self.prefix + r.match(result).group(1)
                metric_value = r.match(result).group(2)
                metrics.append(self.build_metric(
                    metric_name, metric_value, timestamp, tags))
        log.debug("Metrics: %s", metrics)
        return metrics

    def get_metrics(self):
        metrics = []
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        try:
            s.connect((self.HOST, self.PORT))
        except socket.error as e:
            log.error("Unable to connect %s", e)
            if s:
                s.close()
            return metrics

        sent = s.sendall('stats\n')
        data = s.recv(4096)

        if s:
            s.close()

        if not data:
            log.error("No Data Returned from Memcached")
            return metrics
        metrics.extend(self._extract_data(data))
        log.info("Collected %i metrics" % len(metrics))
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

        mm = MemcachedMetrics(options=args)
        gatherer = mm.build_gatherer()
        metrics = gatherer.get_metrics()
        pprint(metrics)
    else:
        mm = MemcachedMetrics(options=args)
        mm.run()
