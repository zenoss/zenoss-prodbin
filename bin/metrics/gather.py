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
import argparse
from collections import defaultdict

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
        if not options.service:
            raise Exception("no service specified for which to gather metrics!")
        self.interval = options.interval
        self.service = options.service
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
        if self.service == "rabbitmq":
            return RabbitMetricGatherer()

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


class RabbitMetricGatherer(MetricGatherer):
    def __init__(self):
        MetricGatherer.__init__(self)

    BASE_QUEUE_URL = 'http://localhost:15672/api/queues/%2Fzenoss/'
    HUB_QUEUE_TYPES = ('invalidations', 'collectorcalls')
    METRIC_PREFIX = 'zenoss.rabbitqueue'

    def get_metrics(self):
        metrics = []
        s = requests.Session()
        s.auth = ('zenoss', 'zenoss')
        result = s.get(self.BASE_QUEUE_URL)
        if result.status_code == 200:
            ts = time.time()
            data = result.json()
            without_consumers_aggregate = defaultdict(lambda: 0)
            for queue in data:
                metrics.extend(self._extract_data(queue, ts, without_consumers_aggregate))
            metrics.extend(self._get_no_consumers_aggregate(without_consumers_aggregate, ts))
        else:
            log.warning("Queue stats request failed: %d, %s", result.status_code, result.text)
        return metrics

    def _extract_data(self, queue, timestamp, without_consumers_aggregate):
        metrics = []
        if not 'zenoss' in queue['name']:
            return metrics

        if not queue.has_key('consumers'):
            log.error('queue %s does not have a consumers item' % queue['name'])
        log.debug('%s: %s', queue['name'], queue['consumers'])
        tags = {'zenoss_queuename': queue['name']}

        for stat in ['consumers', 'messages', 'messages_ready', 'messages_unacknowledged']:
            metric_name = '%s.%s' % (self.METRIC_PREFIX, stat)
            metrics.append(self.build_metric(metric_name, queue[stat], timestamp, tags))

        # message_stats only available for queues that have actual activity
        ack_rate, deliver_rate, deliver_get_rate, publish_rate = 0, 0, 0, 0
        if 'message_stats' in queue:
            message_stats = queue['message_stats']
            for detail in ['ack_details', 'deliver_details', 'deliver_get_details', 'publish_details']:
                if not detail in message_stats:
                    continue
                rate_name = '%s.%s' % (self.METRIC_PREFIX, detail.replace('_details', '_rate'))
                rate_value = message_stats[detail]['rate']
                metrics.append(self.build_metric(rate_name,  rate_value, timestamp, tags))

        # aggregate these
        for qtype in self.HUB_QUEUE_TYPES:
            if queue['name'].startswith('zenoss.queues.hub.%s' % qtype):
                without_consumers_aggregate[qtype] += 1 if queue.get('consumers', 0) == 0 and queue.get('messages', 0) != 0 else 0

        return metrics

    def _get_no_consumers_aggregate(self, without_consumers_aggregate, timestamp):
        metrics = []
        for queue, messages_and_no_consumers in without_consumers_aggregate.iteritems():
            metrics.append(self.build_metric('%s.%s.queues.without.consumers' % (self.METRIC_PREFIX, queue),
                                             messages_and_no_consumers,
                                             timestamp,
                                             tags={'zenoss_queuename': 'zenoss.queues.hub.%s.aggregated' % queue}))
        return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("service", help="the service for which to collect metrics")
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    args = parser.parse_args()

    sm = ServiceMetrics(options=args)
    sm.run()
