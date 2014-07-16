##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

log = logging.getLogger("zen.publisher")

from .utils import basic_auth_string_content
from cookielib import CookieJar
from collections import deque
from twisted.internet import defer, protocol, reactor
from twisted.web.client import Agent, CookieAgent
from twisted.web.iweb import IBodyProducer
from twisted.web.http_headers import Headers
from zope.interface import implements
from txredis import RedisClientFactory

import json as _stdlib_json
from .compat import json


defaultMetricsChannel = "metrics"
defaultMetricBufferSize = 65536
defaultPublishFrequency = 1.0
defaultRedisPort = 6379
defaultMaxOutstandingMetrics = 864000000

bufferHighWater = 4096


class BasePublisher(object):
    """
    Publish metrics to redis
    """

    def __init__(self, buflen, pubfreq):
        self._buflen = buflen
        self._pubfreq = pubfreq
        self._pubtask = None
        self._mq = deque(maxlen=buflen)

    def build_metric(self, metric, value, timestamp, tags):
        return {"metric": metric,
                "value": value,
                "timestamp": timestamp,
                "tags": tags}

    def _publish_failed(self, reason, metrics):
        """
        Push as many of the unpublished metrics as possible back into the
        message queue

        @param reason: what went wrong
        @param metrics: metrics that still need to be published
        @return: the number of metrics still in the queue. Note, this
        will stop the errback chain
        """
        log.info('publishing failed: %s', reason.getErrorMessage())

        open_slots = self._mq.maxlen - len(self._mq)
        self._mq.extendleft(reversed(metrics[-open_slots:]))

        return len(self._mq)

    def _reschedule_pubtask(self, scheduled):
        """
        Reschedule publish task
        @param scheduled: scheduled invocation?
        """
        if not scheduled and self._pubtask:
            self._pubtask.cancel()

        self._pubtask = reactor.callLater(self._pubfreq, self._put, True)

    def _put(self, scheduled):
        """
        Push the buffer of metrics to the specified Redis channel
        @param scheduled: scheduled invocation?
        """
        raise NotImplementedError("method must be overridden")

    def put(self, metric, value, timestamp, tags):
        """
        Wrap the metric, value, timestamp, and uuid in a
        JSON envelop and push it to the specified Redis
        channel

        @param metric: metric being published
        @param value: the metrics value
        @param timestamp: just that
        @param tags: dictionary of tags for the metric
        @return: a deferred that will return the number of metrics still
        in the buffer when fired
        """
        if not self._pubtask:
            self._pubtask = reactor.callLater(self._pubfreq, self._put, True)

        mv = self.build_metric(metric, value, timestamp, tags)
        log.debug("writing: %s", mv)

        self._mq.append(mv)

        if len(self._mq) < bufferHighWater:
            return defer.succeed(len(self._mq))
        else:
            return self._put(False)


class RedisListPublisher(BasePublisher):
    """
    Publish metrics to redis
    """

    def __init__(self,
                 host='localhost',
                 port=defaultRedisPort,
                 buflen=defaultMetricBufferSize,
                 pubfreq=defaultPublishFrequency,
                 channel=defaultMetricsChannel,
                 maxOutstandingMetrics=defaultMetricBufferSize):
        super(RedisListPublisher, self).__init__(buflen, pubfreq)
        self._host = host
        self._port = port
        self._channel = channel
        self._maxOutstandingMetrics = maxOutstandingMetrics
        self._redis = RedisClientFactory()
        self._connection = reactor.connectTCP(self._host,
                                              self._port,
                                              self._redis)
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)

    def build_metric(self, metric, value, timestamp, tags):
        """
        Override base method to work with strings instead of dicts
        """
        m = BasePublisher.build_metric(self, metric, value, timestamp, tags)
        try:
            return json.dumps(m)
        except (OverflowError, ValueError):
            # ujson can't serialize numbers larger than 64-bit signed int
            # (see https://github.com/esnme/ultrajson/issues/67).
            # Fall back to stdlib json, which does not have this limitation.
            return _stdlib_json.dumps(m)

    def _metrics_published(self, llen, metricCount):
        """
        Callback that logs successful publishing of metrics and
        clears the metrics buffer

        @param llen: number of metrics in Redis after publishing
        @return: the number of metrics still in the queue
        """
        log.info('published %d metrics to redis', metricCount)
        return 0

    def _put(self, scheduled, reschedule=True):
        """
        Push the buffer of metrics to the specified Redis channel
        @param scheduled: Whether it was a scheduled invocation
        """
        if reschedule:
            self._reschedule_pubtask(scheduled)

        if len(self._mq) == 0:
            return defer.succeed(0)

        if self._connection.state == 'connected':
            log.debug('trying to publish %d metrics', len(self._mq))

            metrics = list(self._mq)
            self._mq.clear()

            @defer.inlineCallbacks
            def _flush():
                client = self._redis.client
                yield client.multi()
                yield client.lpush(self._channel, *metrics)
                yield client.ltrim(self._channel, 0, self._maxOutstandingMetrics - 1)
                result, _ = yield client.execute()
                try:
                    yield self._metrics_published(result,
                                                  metricCount=len(metrics))
                except Exception:
                    yield self._publish_failed(metrics=metrics)

            return _flush()

    def _shutdown(self):
        def disconnect(c):
            log.debug('shutting down [disconnecting]')
            if self._connection.state == 'connected':
                self._connection.disconnect()
            log.debug('shutting down [disconnected]')

        log.debug('shutting down')
        if self._connection.state != 'connected':
            log.debug('shutting down [not connected: %s]',
                      self._connection.state)
        elif len(self._mq):
            log.debug('shutting down [publishing]')
            try:
                d = self._put(False, reschedule=False)
                d.addCallback(disconnect)
                return d
            except Exception as x:
                log.exception('shutting down [publishing failed: %s]', x)
        else:
            disconnect(True)


class HttpPostPublisher(BasePublisher):
    """
    Publish metrics via HTTP POST
    """

    def __init__(self,
                 username,
                 password,
                 url='https://localhost:8443/api/metrics/store',
                 buflen=defaultMetricBufferSize,
                 pubfreq=defaultPublishFrequency):
        super(HttpPostPublisher, self).__init__(buflen, pubfreq)
        self._username = username
        self._password = password
        self._cookieJar = CookieJar()
        self._agent = CookieAgent(Agent(reactor), self._cookieJar)
        self._url = url
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)

    def _metrics_published(self, response, llen):
        if response.code != 200:
            raise IOError("Expected HTTP 200, but received %d" % response.code)
        log.debug("published %d metrics and received response: %s",
                  llen, response.code)
        finished = defer.Deferred()
        response.deliverBody(ResponseReceiver(finished))
        return finished

    def _response_finished(self, result):
        # The most likely result is the HTTP response from a successful POST,
        # which should be JSON formatted.
        if isinstance(result, str):
            log.debug("response was: %s", json.loads(result))
        # We could be called back because _publish_failed was called before us
        elif isinstance(result, int):
            log.info("queue still contains %d metrics", result)
        # Or something strange could have happend
        else:
            log.warn("Unexpected result: %s", result)

    def _shutdown(self):
        log.debug('shutting down [publishing]')
        if len(self._mq):
            self._make_request()

    def _make_request(self):
        metrics = list(self._mq)
        self._mq.clear()

        serialized_metrics = json.dumps({"metrics": metrics})
        body_writer = StringProducer(serialized_metrics)

        d = self._agent.request(
            'POST', self._url, Headers({
                'Authorization': [basic_auth_string_content(
                    self._username, self._password)],
                'User-Agent': ['Zenoss Metric Publisher'],
                'Content-Type': ['application/json']}),
            body_writer)

        d.addCallbacks(self._metrics_published, errback=self._publish_failed,
                       callbackArgs=[len(metrics)], errbackArgs=[metrics])
        d.addCallbacks(self._response_finished, errback=self._publish_failed,
                       errbackArgs=[metrics])
        return d

    def _put(self, scheduled):
        """
        Push the buffer of metrics to the specified Redis channel
        @param scheduled: scheduled invocation?
        """
        self._reschedule_pubtask(scheduled)

        if len(self._mq) == 0:
            return defer.succeed(0)

        log.debug('trying to publish %d metrics', len(self._mq))
        return self._make_request()


class StringProducer(object):
    implements(IBodyProducer)
    """
    Implements twisted interface for writing a string to HTTP output stream
    """

    def __init__(self, postBody):
        self._post_body = postBody
        self.length = len(postBody)

    def startProducing(self, consumer):
        consumer.write(self._post_body)
        return defer.succeed(None)

    def stopProducing(self):
        pass

    def pauseProducing(self):
        pass

    def resumeProducing(self):
        pass


class ResponseReceiver(protocol.Protocol):
    """
    Captures HTTP response from POST
    """

    def __init__(self, deferred):
        self._buffer = ''
        self._deferred = deferred

    def dataReceived(self, data):
        self._buffer += data

    def connectionLost(self, reason):
        log.debug("connection closed")
        self._deferred.callback(self._buffer)
