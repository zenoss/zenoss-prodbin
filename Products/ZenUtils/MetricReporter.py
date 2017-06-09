##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

import json
import logging
import os
import requests
import time

from metrology.instruments import (
    Counter,
    Gauge,
    Histogram,
    Meter,
    Timer,
    UtilizationTimer,
)

from metrology.reporter.base import Reporter

log = logging.getLogger("zen.metricreporter")


class MetricReporter(Reporter):

    def __init__(self, **options):
        super(MetricReporter, self).__init__(interval=30)
        self.prefix = options.get('prefix', "")
        self.metric_destination = os.environ.get("CONTROLPLANE_CONSUMER_URL", "")
        if self.metric_destination == "":
            self.metric_destination = "http://localhost:22350/api/metrics/store"
        self.session = None
        self.tags = None
        self.tags = {
            'serviceId': os.environ.get('CONTROLPLANE_SERVICE_ID', ''),
            'instance': os.environ.get('CONTROLPLANE_INSTANCE_ID', ''),
            'hostId': os.environ.get('CONTROLPLANE_HOST_ID', ''),
            'tenantId': os.environ.get('CONTROLPLANE_TENANT_ID', ''),
        }

    def write(self):
        metrics = []
        snapshot_keys = ['median', 'percentile_95th']
        for name, metric in self.registry:
            log.debug("metric info: %s, %s", name, metric)
            if isinstance(metric, Meter):
                keys = ['count', 'one_minute_rate', 'five_minute_rate',
                        'fifteen_minute_rate', 'mean_rate']
                metrics.extend(self.log_metric(name, metric, keys))
            if isinstance(metric, Gauge):
                keys = ['value']
                metrics.extend(self.log_metric(name, metric, keys))
            if isinstance(metric, UtilizationTimer):
                keys = ['count', 'one_minute_rate', 'five_minute_rate',
                        'fifteen_minute_rate', 'mean_rate', 'min', 'max',
                        'mean', 'stddev', 'one_minute_utilization',
                        'five_minute_utilization', 'fifteen_minute_utilization',
                        'mean_utilization']
                metrics.extend(self.log_metric(name, metric, keys, snapshot_keys))
            if isinstance(metric, Timer):
                keys = ['count', 'one_minute_rate', 'five_minute_rate',
                        'fifteen_minute_rate', 'mean_rate', 'min', 'max', 'mean',
                        'stddev']
                metrics.extend(self.log_metric(name, metric, keys, snapshot_keys))
            if isinstance(metric, Counter):
                keys = ['count']
                metrics.extend(self.log_metric(name, metric, keys))
            if isinstance(metric, Histogram):
                keys = ['count', 'min', 'max', 'mean', 'stddev']
                metrics.extend(self.log_metric(name, metric, keys, snapshot_keys))
        try:
            if not self.session:
                self.session = requests.Session()
            self.session.headers.update({'Content-Type': 'application/json'})
            self.session.headers.update({'User-Agent': 'Zenoss Service Metrics'})
            post_data = {'metrics': metrics}
            log.debug("Sending metric payload: %s" % post_data)
            response = self.session.post(self.metric_destination,
                                         data=json.dumps(post_data))
            if response.status_code != 200:
                log.warning("Problem submitting metrics: %d, %s",
                            response.status_code, response.text.replace('\n', '\\n'))
                self.session = None
            else:
                log.debug("%d Metrics posted" % len(metrics))
        except Exception as e:
            log.error(e)

    def log_metric(self, name, metric, keys, snapshot_keys=None):
        results = []

        if snapshot_keys is None:
            snapshot_keys = []

        metric_name = self.prefix + name if self.prefix else name
        ts = time.time()
        try:
            for stat in keys:
                whole_metric_name = "%s.%s" % (metric_name, stat)
                results.append({"metric": whole_metric_name,
                                "value": getattr(metric, stat),
                                "timestamp": ts,
                                "tags": self.tags})

            if hasattr(metric, 'snapshot'):
                snapshot = metric.snapshot
                for stat in snapshot_keys:
                    whole_metric_name = "%s.%s" % (metric_name, stat)
                    results.append({"metric": whole_metric_name,
                                    "value": getattr(snapshot, stat),
                                    "timestamp": ts,
                                    "tags": self.tags})
        except Exception as e:
            log.error(e)
        return results

