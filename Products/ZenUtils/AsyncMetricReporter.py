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

from MetricReporter import MetricReporter

log = logging.getLogger("zen.metricreportera")

class AsyncMetricReporter(MetricReporter):
    def __init__(self, **options):
        '''
        AsyncMetricReporter's __init__ differs from MetricReporter
        by requiring a MetricWriter.
        '''
        super(AsyncMetricReporter, self).__init__(**options)
        self.metricwriter = options.get('metricwriter', None)

    def log_metric(self, name, metric, keys, snapshot_keys=None):
        if self.metricwriter is None:
            log.warn("No metricwriter specified.")
            return []

        if snapshot_keys is None:
            snapshot_keys = []

        metric_name = self.prefix + name if self.prefix else name
        ts = time.time()
        try:
            for stat in keys:
                whole_metric_name = "%s.%s" % (metric_name, stat)
                log.debug("Writing metric %s", metric_name)
                self.metricwriter.write_metric(
                    metric=whole_metric_name,
                    value=getattr(metric, stat),
                    timestamp=ts,
                    tags=self.tags)

            if hasattr(metric, 'snapshot'):
                snapshot = metric.snapshot
                for stat in snapshot_keys:
                    whole_metric_name = "%s.%s" % (metric_name, stat)
                    log.debug("Writing snapshot metric %s", metric_name)
                    self.metricwriter.write_metric(
                        metric=whole_metric_name,
                        value=getattr(snapshot, stat),
                        timestamp=ts,
                        tags=self.tags)

        except Exception as e:
            log.error(e)

        # Return [] so self._post_metrics() has nothing to do.
        return []
