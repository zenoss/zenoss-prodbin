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

import requests

log = logging.getLogger('zenoss.servicemetrics')
logging.basicConfig()
log.setLevel(logging.INFO)


class ServiceMetrics:
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
            log.warning("Problem submitting metrics: %d, %s" % response.status_code, response.text)
            self.session = None
        else:
            log.debug("%d Metrics posted" % len(metrics))


class MetricGatherer:
    def __init__(self):
        self.service_id = os.environ.get("CONTROLPLANE_SERVICED_ID", "")
        self.instance_id = os.environ.get("CONTROLPLANE_INSTANCE_ID", "")
        self.host_id = os.environ.get("CONTROLPLANE_HOST_ID", "")
        self.tenant_id = os.environ.get("CONTROLPLANE_TENANT_ID", "")
        self.tags = {
            "serviceId": self.service_id,
            "instance": self.instance_id,
            "hostId": self.host_id,
            "tenantId": self.tenant_id
        }

    def build_metric(self, name, value, timestamp, tags=None):
        _value = self.float_value(value)
        if tags:
            tags.update(self.tags)
        else:
            tags = self.tags
        return {"metric": name,
                "value": _value,
                "timestamp": timestamp,
                "tags": tags}

    @staticmethod
    def float_value(value):
        if isinstance(value, float):
            return value

        if isinstance(value, (int, long, str)):
            return float(value)
        return None


class RabbitMetricGatherer(MetricGatherer):
    def __init__(self):
        MetricGatherer.__init__(self)

    BASE_QUEUE_URL = 'http://localhost:15672/api/queues/%2Fzenoss/'

    def get_metrics(self):
        metrics = []
        s = requests.Session()
        s.auth = ('zenoss', 'zenoss')
        result = s.get(self.BASE_QUEUE_URL)
        if result.status_code == 200:
            ts = time.time()
            data = result.json()
            for queue in data:
                if 'zenoss' in queue['name']:
                    # TODO: filter ephemeral queues, like invalidations and collectorcalls.
                    # maybe do aggregate metrics like 'queues with no consumers', i.e. unmonitored

                    self._extract_data(metrics, queue, ts)
        else:
            log.warning("Queue stats request failed: %d, %s" % result.status_code, result.text)
        return metrics

    def _extract_data(self, metrics, queue, ts):
        log.debug('%s: %s' % (queue['name'], queue['consumers']))
        prefix = 'zenoss.rabbitqueue'
        tags = {'name': queue['name']}
        consumers = queue['consumers']
        metrics.append(MetricGatherer.build_metric(self, "%s.consumers" % prefix, consumers, ts, tags))
        messages = queue['messages']
        metrics.append(MetricGatherer.build_metric(self, "%s.messages" % prefix, messages, ts, tags))
        ready = queue['messages_ready']
        metrics.append(MetricGatherer.build_metric(self, "%s.messages_ready" % prefix, ready, ts, tags))
        messages_unacknowledged = queue['messages_unacknowledged']
        metrics.append(MetricGatherer.build_metric(self, "%s.messages_unacknowledged" %
                                                   prefix, messages_unacknowledged, ts, tags))
        # message_stats only available for queues that have actual activity
        ack_rate, deliver_rate, deliver_get_rate, publish_rate = 0, 0, 0, 0
        if 'message_stats' in queue:
            ack_rate = queue['message_stats']['ack_details']['rate']
            deliver_rate = queue['message_stats']['deliver_details']['rate']
            deliver_get_rate = queue['message_stats']['deliver_get_details']['rate']
            publish_rate = queue['message_stats']['publish_details']['rate']
        metrics.append(MetricGatherer.build_metric(self, "%s.ack_rate" % prefix, ack_rate, ts, tags))
        metrics.append(MetricGatherer.build_metric(self, "%s.deliver_rate" % prefix, deliver_rate, ts, tags))
        metrics.append(MetricGatherer.build_metric(self, "%s.deliver_get_rate" %
                                                   prefix, deliver_get_rate, ts, tags))
        metrics.append(MetricGatherer.build_metric(self, "%s.publish_rate" % prefix, publish_rate, ts, tags))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("service", help="the service for which to collect metrics")
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    args = parser.parse_args()

    sm = ServiceMetrics(options=args)
    sm.run()
