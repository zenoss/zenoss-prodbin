##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from collections import deque
import datetime
import json
import logging
import numbers
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

from .utils import datetime_millis


BATCHSIZE = 100

def sanitize_field(value):
    # ensure that a value is suitable for use in a metadataField, that is,
    # that it is a scalar or list of scalars

    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Number):
        return value
    if isinstance(value, basestring):
        return value
    if isinstance(value, list):
        return [sanitize_field(x) for x in value]

    # Not a valid type for a metadata field, so force it into a string
    return unicode(value)

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
        self._useHTTPS = useHTTPS
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
    def __init__(self,
                 address,
                 apiKey,
                 useHTTPS=True,
                 source=None,
                 buflen=defaultMetricBufferSize,
                 pubfreq=defaultPublishFrequency):
        super(CloudMetricPublisher, self).__init__(
            address, apiKey, useHTTPS, source, buflen, pubfreq)

        self._sent_daemon_model = False
        self._model_publisher = None


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

        message = self.build_metric(metric, value, timestamp, tags)
        if message:
            return super(CloudMetricPublisher, self).put(message)
        else:
            return defer.succeed(len(self._mq))

    def model_publisher(self):
        if not self._model_publisher:
            self._model_publisher = CloudModelPublisher(
                self._address,
                self._apiKey,
                self._useHTTPS,
                self._source,
                self._buflen)

        return self._model_publisher

    def publish_model(self, name, dimensions, metadataFields):
        model = {
            'timestamp': datetime_millis(datetime.datetime.utcnow()),
            'dimensions': dimensions,
            'metadataFields': metadataFields
        }
        model['metadataFields']['name'] = name

        self.model_publisher().put(model)


    def build_metric(self, metricName, value, timestamp, tags):
        metric = {
            "metric": metricName,
            "value": sanitized_float(value),
            "timestamp": long(timestamp * 1000),
            "dimensions": {
                'device': tags.get('device', ''),
                'component': tags.get('contextUUID', ''),
                'source': self._source
            },
            "metadataFields": {
                'source-type': "zenoss.nub"
            }
        }

        # For internal metrics, include all tags.
        if tags.get('internal', False):

            del metric["dimensions"]["device"]
            del metric["dimensions"]["component"]
            metric["dimensions"]["daemon"] = tags.get('daemon', '')

            for t, v in tags.iteritems():
                if t == 'daemon':
                    continue
                metric['metadataFields'][t] = sanitize_field(v)

            # publish a model as well, the first tim we're called.
            if self._sent_daemon_model is False:
                self.publish_model(
                    metric["dimensions"]["daemon"],
                    metric['dimensions'],
                    metric['metadataFields'])
                self._sent_daemon_model = True

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

        return metric

    def serialize_messages(self, messages):
        return json.dumps({
            "detailedResponse": True,
            "metrics": messages}, indent=4)


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

    def serialize_messages(self, messages):
        return json.dumps({
            "detailedResponse": True,
            "models": messages}, indent=4)
