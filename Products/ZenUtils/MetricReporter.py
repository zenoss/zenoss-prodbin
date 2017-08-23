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
from twisted.internet import reactor, defer, task

from metrology.registry import registry
from astrolabe.interval import Interval
from itertools import izip
from collections import deque

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


class TimeOnce(object):
    """
    a simple context manager to time something and save tag values and
    a measurement.
    """
    def __init__(self, gauge, *args):
        if len(gauge.tagKeys) != len(args):
            raise RuntimeError('The number of tag values provided does not match the number of configured tag keys')
        self.gauge = gauge
        self.tagValues = args
    def __enter__(self):
        self.interval = Interval.now()
    def __exit__(self, *args):
        self.gauge.queue.appendleft(self.tagValues + (self.interval.stop(),))


class QueueGauge(object):
    """
    This instrument contains simple point-in-time measurements like a gauge.
    Unlike a gauge, however, it:
      - can be configured to have tags whose values can vary with each measurement
      - contains a queue of values with tag values, which are read only once each
    Many values or none can be written to this instrument between cycles of its
    reporter, so for it many or no values will be published.
    Calling an instance returns something which should append to the instances
    queue a tuple, which should contain 1 value for each tagKey of the instance,
    followed by a measurement.
    """
    def __init__(self, *args):
        self.newContextManager = args[0] if callable(args[0]) else TimeOnce
        self.tagKeys = args if not callable(args[0]) else args[1:]
        self.queue = deque()
    def __call__(self, *args):
        return self.newContextManager(self, *args)


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
        self._write()

    def _write(self):
        metrics = getMetrics(self.registry, self.tags, self.prefix)
        try:
            self.postMetrics(metrics)
        except Exception as e:
            log.error(e)

    def postMetrics(self, metrics):
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


class TwistedMetricReporter(object):
    def __init__(self, interval=30, metricWriter=None, tags={}, *args, **options):
        super(TwistedMetricReporter, self).__init__()
        self.registry = options.get('registry', registry)
        self.prefix = options.get('prefix', "")
        self.metricWriter = metricWriter
        self.interval = interval
        self.tags = {}
        self.tags.update(tags)
        self._stopped = False
        self._loop = task.LoopingCall(self.postMetrics)

    def start(self):
        def doStart():
            self._loop.start(self.interval, now=False)

        reactor.callWhenRunning(doStart)
        reactor.addSystemEventTrigger('before', 'shutdown', self.stop)

    @defer.inlineCallbacks
    def stop(self):
        if not self._stopped:
            self._stopped = True
            self._loop.stop()
            yield self.postMetrics()

    @defer.inlineCallbacks
    def postMetrics(self):
        try:
            for metric in getMetrics(self.registry, self.tags, self.prefix):
                yield self.metricWriter.write_metric(metric['metric'], metric['value'], metric['timestamp'],
                                                    metric['tags'])
        except Exception:
            log.exception("Error writing metrics")


def getMetrics(mRegistry, tags, prefix):
    metrics = []
    snapshot_keys = ['median', 'percentile_95th']
    for name, metric in mRegistry:
        log.debug("metric info: %s, %s", name, metric)
        if isinstance(metric, Meter):
            keys = ['count', 'one_minute_rate', 'five_minute_rate',
                    'fifteen_minute_rate', 'mean_rate']
            metrics.extend(log_metric(name, metric, keys, tags, prefix))
        if isinstance(metric, Gauge):
            keys = ['value']
            metrics.extend(log_metric(name, metric, keys, tags, prefix))
        if isinstance(metric, QueueGauge):
            metrics.extend(log_queue_gauge(name, metric, tags, prefix))
        if isinstance(metric, UtilizationTimer):
            keys = ['count', 'one_minute_rate', 'five_minute_rate',
                    'fifteen_minute_rate', 'mean_rate', 'min', 'max',
                    'mean', 'stddev', 'one_minute_utilization',
                    'five_minute_utilization', 'fifteen_minute_utilization',
                    'mean_utilization']
            metrics.extend(log_metric(name, metric, keys, tags, prefix, snapshot_keys))
        if isinstance(metric, Timer):
            keys = ['count', 'one_minute_rate', 'five_minute_rate',
                    'fifteen_minute_rate', 'mean_rate', 'min', 'max', 'mean',
                    'stddev']
            metrics.extend(log_metric(name, metric, keys, tags, prefix, snapshot_keys))
        if isinstance(metric, Counter):
            keys = ['count']
            metrics.extend(log_metric(name, metric, keys, tags, prefix))
        if isinstance(metric, Histogram):
            keys = ['count', 'min', 'max', 'mean', 'stddev']
            metrics.extend(log_metric(name, metric, keys, tags, prefix, snapshot_keys))
    return metrics

def log_queue_gauge(name, metric, tags, prefix):
    """
    A QueueGauge needs this unique handler because it does not contain a
    fixed number of values.
    """
    results = []

    metric_name = prefix + name if prefix else name
    ts = time.time()
    whole_metric_name = "{}.value".format(metric_name)
    try:
        while metric.queue:
            # each stat should be a tuple with 1 more member than metric.tagKeys
            stat = metric.queue.pop()
            qtags = tags.copy()
            qtags.update(izip(metric.tagKeys, stat))
            results.append({"metric": whole_metric_name,
                            "value": stat[-1],
                            "timestamp": ts,
                            "tags": qtags})

    except Exception as e:
        log.error(e)
    return results

def log_metric(name, metric, keys, tags, prefix, snapshot_keys=None):
    results = []

    if snapshot_keys is None:
        snapshot_keys = []

    metric_name = prefix + name if prefix else name
    ts = time.time()
    try:
        for stat in keys:
            whole_metric_name = "%s.%s" % (metric_name, stat)
            results.append({"metric": whole_metric_name,
                            "value": getattr(metric, stat),
                            "timestamp": ts,
                            "tags": tags})

        if hasattr(metric, 'snapshot'):
            snapshot = metric.snapshot
            for stat in snapshot_keys:
                whole_metric_name = "%s.%s" % (metric_name, stat)
                results.append({"metric": whole_metric_name,
                                "value": getattr(snapshot, stat),
                                "timestamp": ts,
                                "tags": tags})
    except Exception as e:
        log.error(e)
    return results
