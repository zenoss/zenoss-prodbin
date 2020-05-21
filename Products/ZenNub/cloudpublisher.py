##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from collections import deque
import json
import logging
import os
import sys

LOG = logging.getLogger("zen.cloudpublisher")

from twisted.internet import defer, reactor, ssl
from twisted.web.client import Agent, BrowserLikePolicyForHTTPS
from twisted.web.http_headers import Headers

from Products.ZenHub.metricpublisher.publisher import (
    defaultMetricBufferSize,
    defaultPublishFrequency,
    bufferHighWater,
    StringProducer,
    ResponseReceiver,
    sanitized_float
)
from Products.ZenUtils.MetricServiceRequest import getPool


API_KEY_FIELD     = "zenoss-api-key"
SOURCE_FIELD      = "source"
SOURCE_TYPE_FIELD = "source-type"

SOURCE_TYPE       = "zenoss/zennub"

BATCHSIZE = 100


class NoVerificationPolicy(BrowserLikePolicyForHTTPS):
    # disable certificate validation completely.    Maybe not the best idea.
    # we can make this a bit more specific, surely.
    def creatorForNetloc(self, hostname, port):
        return ssl.CertificateOptions(verify=False)


class CloudPublisher(object):
    """
    Publish messages (metric, model, event) to a zenoss cloud datareceiver
    endpoint over http/https.
    """

    def __init__(self,
                 address,
                 apiKey,
                 useHTTPS=True,
                 source=None,
                 buflen=defaultMetricBufferSize,
                 pubfreq=defaultPublishFrequency):
        self._buflen = buflen
        self._pubfreq = pubfreq
        self._pubtask = None
        self._mq = deque(maxlen=buflen)

        self._agent = Agent(reactor, NoVerificationPolicy(), pool=getPool())
        self._address = address
        self._apiKey = apiKey
        self._source = source

        if source is None:
            raise Exception("zenoss-source must be specified.")

        if address is None:
            raise Exception("zenoss-address must be specified.")

        scheme = 'https' if useHTTPS else 'http'
        self._url = self.get_url(scheme, address)

        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)

    @property
    def log(self):
        return LOG

    @property
    def user_agent(self):
        return 'Zenoss Cloud Publisher'

    def get_url(self, scheme, address):
        raise NotImplementedError("method must be overridden")

    def serialize_messages(self, messages):
        raise NotImplementedError("method must be overridden")

    def _publish_failed(self, reason, messages):
        """
        Push as many of the unpublished messages as possible back into the
        message queue

        @param reason: what went wrong
        @param messages: messages that still need to be published
        @return: the number of messages still in the queue. Note, this
        will stop the errback chain
        """
        self.log.info('publishing failed: %s', getattr(reason, 'getErrorMessage', reason.__str__)())

        open_slots = self._mq.maxlen - len(self._mq)
        self._mq.extendleft(reversed(messages[-open_slots:]))

        return len(self._mq)

    def _reschedule_pubtask(self, scheduled):
        """
        Reschedule publish task
        @param scheduled: scheduled invocation?
        """
        if not scheduled and self._pubtask:
            self._pubtask.cancel()

        self._pubtask = reactor.callLater(self._pubfreq, self._putLater, True)

    def put(self, message):
        """
        Enqueue the specified message for publishing

        @return: a deferred that will return the number of messages still
        in the buffer when fired
        """
        if not self._pubtask:
            self._pubtask = reactor.callLater(self._pubfreq, self._putLater, True)

        self.log.debug("writing: %s", message)

        self._mq.append(message)

        if len(self._mq) < bufferHighWater:
            return defer.succeed(len(self._mq))
        else:
            return self._put(False)


    def _put(self, scheduled):
        """
        Push the buffer of messages
        @param scheduled: scheduled invocation?
        """
        if scheduled:
            self._reschedule_pubtask(scheduled)

        if len(self._mq) == 0:
            return defer.succeed(0)

        self.log.debug('trying to publish %d messages', len(self._mq))
        return self._make_request()

    def _putLater(self, scheduled):
        def handleError(val):
            self.log.debug("Error sending metric: %s", val)
        d = self._put(scheduled=scheduled)
        d.addErrback(handleError)

    def _make_request(self):
        messages = []
        for x in xrange(BATCHSIZE):
            if not self._mq:
                break
            messages.append(self._mq.popleft())
        if not messages:
            self.log.debug('no messages to send')
            return defer.succeed(None)

        body_writer = StringProducer(self.serialize_messages(messages))

        headers = Headers({
            'User-Agent': [self.user_agent],
            'Content-Type': ['application/json']})

        if self._apiKey:
            headers.addRawHeader('zenoss-api-key', self._apiKey)

        self.log.debug("Posting %s messages" % len(messages))
        d = self._agent.request(
            'POST', self._url, headers,
            body_writer)

        d.addCallbacks(self._messages_published, errback=self._publish_failed,
        callbackArgs = [len(messages), len(self._mq)], errbackArgs = [messages])
        d.addCallbacks(self._response_finished, errback=self._publish_failed,
                       errbackArgs = [messages])

        return d

    def _messages_published(self, response, llen, remaining=0):
        if response.code != 200:
            # raise IOError("Expected HTTP 200, but received %d from %s" % (response.code, self._url))
            pass

        self.log.debug("published %d messages and received response: %s",
                  llen, response.code)
        finished = defer.Deferred()
        response.deliverBody(ResponseReceiver(finished))
        if remaining:
            reactor.callLater(0, self._putLater, False)
        return finished

    def _response_finished(self, result):
        # The most likely result is the HTTP response from a successful POST.
        if isinstance(result, str):
            self.log.debug("response was: %s", result)
        # We could be called back because _publish_failed was called before us
        elif isinstance(result, int):
            self.log.info("queue still contains %d messages", result)
        # Or something strange could have happend
        else:
            self.log.warn("Unexpected result: %s", result)

    def _shutdown(self):
        self.log.debug('shutting down CloudPublisher [publishing %s messages]' % len(self._mq))
        if len(self._mq):
            return self._make_request()


class CloudMetricPublisher(CloudPublisher):

    def get_url(self, scheme, address):
        return "{scheme}://{address}/v1/data-receiver/metrics".format(
            scheme=scheme, address=address)

    @property
    def user_agent(self):
        return 'Zenoss Metric Cloud Publisher'

    @property
    def log(self):
        if getattr(self, "_metriclog", None) is None:
            self._metriclog = logging.getLogger("zen.cloudpublisher.metric")
        return self._metriclog

    def put(self, metric, value, timestamp, tags):
        """
        Build a message from the metric, value, timestamp, and tags, and
        push it into the message queue to be sent.

        @param metric: metric being published
        @param value: the metric's value
        @param timestamp: just that
        @param tags: dictionary of tags for the metric
        @return: a deferred that will return the number of metrics still
        in the buffer when fired
        """

        message = self.build_taggedmetric(metric, value, timestamp, tags)
        return super(CloudMetricPublisher, self).put(message)


    def build_taggedmetric(self, metricName, value, timestamp, tags):
        metric = {
            "metric": metricName,
            "value": sanitized_float(value),
            "timestamp": long(timestamp * 1000)
        }

        # For internal metrics, include all tags.
        if tags.get('internal', False):
            metric['tags'] = {}
            for t, v in tags.iteritems():
                metric['tags'][t] = str(v)
            metric['tags']['source'] = self._source
            return metric

        # Set the metric name correctly.
        # We want to be using datasource_datapoint naming.  In order to do this,
        # we rely upon collector daemons and their config services to make use of
        # the metricPrefix metadata field to change the formatting of the metric
        # name from <device id>/<dp id> to <ds id>/<dp_id>
        if '/' in metricName:
            if 'device' in tags and metricName.startswith(tags['device']):
                log.debug("Warning: metric name %s appears to start with a device id, rather than a datasource name", metric['metric'])

            metric['metric'] = metricName.replace('/', '_', 1)

        metric['tags'] = {
            'source': self._source,
            'device': tags.get('device', ''),
            'component': tags.get('contextUUID', '')
        }

        if metric['tags']['device'] == metric['tags']['component']:
            # no need for this.
            del metric['tags']['component']

        return metric

    def serialize_messages(self, messages):
        return json.dumps({"taggedMetrics": messages}, indent=4)


class CloudModelPublisher(CloudPublisher):
    def get_url(self, scheme, address):
        return "{scheme}://{address}/v1/data-receiver/models".format(
            scheme=scheme, address=address)

    @property
    def user_agent(self):
        return 'Zenoss Model Cloud Publisher'

    @property
    def log(self):
        if getattr(self, "_modellog", None) is None:
            self._modellog = logging.getLogger("zen.cloudpublisher.model")
        return self._modellog



