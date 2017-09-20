#!/usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
import time
import argparse
import os
import re
from collections import defaultdict

import requests

from gather import MetricGatherer, ServiceMetrics

log = logging.getLogger('zenoss.servicemetrics')
logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log.setLevel(logging.INFO)


# _KEYVALUE and globalConfToDict COPIED from Products.ZenUtils.GlobalConfig
# to avoid having to use the entire zenoss python env just to read 1 file
_KEYVALUE = re.compile("^[\s ]*(?P<key>[a-z_]+[a-z0-9_-]*)[\s]+(?P<value>[^\s#]+)", re.IGNORECASE).search

def globalConfToDict():
    settings = {}
    # the line below is the only change, previously used zenPath()
    globalConfFile = '/opt/zenoss/etc/global.conf'
    if os.path.exists(globalConfFile):
        with open(globalConfFile, 'r') as f:
            for line in f.xreadlines():
                match = _KEYVALUE(line)
                if match:
                    value = match.group('value')
                    if value.isdigit():
                        value = int(value)
                    settings[match.group('key')] = value
    return settings


class RabbitMetrics(ServiceMetrics):

    def build_gatherer(self):
        return RabbitMetricGatherer()


class RabbitMetricGatherer(MetricGatherer):
    def __init__(self):
        super(RabbitMetricGatherer, self).__init__()
        config = globalConfToDict()
        self._amqpuser = config.get('amqpuser', 'zenoss')
        self._amqppassword = config.get('amqppassword', 'zenoss')

    BASE_QUEUE_URL = 'http://localhost:15672/api/queues/%2Fzenoss/'
    HUB_QUEUE_TYPES = ('invalidations', 'collectorcalls')
    METRIC_PREFIX = 'zenoss.rabbitqueue'

    def get_metrics(self):
        metrics = []
        s = requests.Session()
        s.auth = (self._amqpuser, self._amqppassword)
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
        
        if not queue.has_key('consumers'):
            log.error('queue %s does not have a consumers item' % queue['name'])
        log.debug('%s: %s', queue['name'], queue['consumers'])
        tags = {'zenoss_queuename': queue['name']}

        for stat in ['consumers', 'messages', 'messages_ready', 'messages_unacknowledged']:
            metric_name = '%s.%s' % (self.METRIC_PREFIX, stat)
            metrics.append(self.build_metric(metric_name, queue[stat], timestamp, tags))

        if queue['name'] == 'zenoss.queues.zep.zenevents':
            stat = 'messages'
            metric_name = '%s.zenevents.%s' % (self.METRIC_PREFIX, stat)
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



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--interval", dest="interval", type=float,
                        default=30, help="polling interval in seconds")
    args = parser.parse_args()

    rm = RabbitMetrics(options=args)
    rm.run()
