#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import os
import logging
import traceback
import json
import time

import requests

log = logging.getLogger('zenoss.servicemetrics')
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log.setLevel(logging.INFO)


class ServiceMetrics(object):
    """
    Simple process that creates a metric gatherer, loops calling for
    internal metrics, then posts those metrics to a consumer.
    """
    DEFAULT_CONSUMER = "http://localhost:22350/api/metrics/store"

    def __init__(self, options):
        self.interval = options.interval
        self.metric_destination = os.environ.get("CONTROLPLANE_CONSUMER_URL", "")
        if self.metric_destination == "":
            self.metric_destination = self.DEFAULT_CONSUMER
        self.session = None

    def run(self):
        gatherer = self.build_gatherer()
        while True:
            time.sleep(self.interval)
            try:
                metrics = gatherer.get_metrics()
                self.push(metrics)
            except Exception:
                log.warning("Failed to gather metrics: " + traceback.format_exc())

    def build_gatherer(self):
        """
        Loads up an object that can gather metrics.
        :return: an instance of an object that implements get_metrics()
        """
        raise NotImplementedError()

    def push(self, metrics):
        if not self.session:
            self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.session.headers.update({'User-Agent': 'Zenoss Service Metrics'})
        post_data = {'metrics': metrics}
        response = self.session.post(self.metric_destination, data=json.dumps(post_data))
        if response.status_code != 200:
            log.warning("Problem submitting metrics: %d, %s", response.status_code, response.text)
            self.session = None
        else:
            log.debug("%d Metrics posted", len(metrics))


class MetricGatherer(object):

    def build_metric(self, name, value, timestamp, tags=None):
        try:
            _value = float(value)
        except ValueError as ve:
            _value = None
        if not tags:
            tags = {}
        return {"metric": name,
                "value": _value,
                "timestamp": timestamp,
                "tags": tags}
