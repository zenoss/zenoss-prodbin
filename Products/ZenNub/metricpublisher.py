##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging
import os
import sys

log = logging.getLogger("zen.cloudpublisher")

from twisted.internet import defer, reactor, ssl
from twisted.web.client import Agent, BrowserLikePolicyForHTTPS
from twisted.web.http_headers import Headers

from Products.ZenHub.metricpublisher.publisher import (
    BasePublisher,
    defaultMetricBufferSize,
    defaultPublishFrequency,
    StringProducer,
    ResponseReceiver
)
from Products.ZenUtils.MetricServiceRequest import getPool


API_KEY_FIELD     = "zenoss-api-key";
SOURCE_FIELD      = "source";
SOURCE_TYPE_FIELD = "source-type";

SOURCE_TYPE       = "zenoss/zennub";

BATCHSIZE = 100


class NoVerificationPolicy(BrowserLikePolicyForHTTPS):
    # disable certificate validation completely.    Maybe not the best idea.
    # we can make this a bit more specific, surely.
    def creatorForNetloc(self, hostname, port):
        return ssl.CertificateOptions(verify=False)


class CloudPublisher(BasePublisher):
    """
    Publish metrics to a zenoss cloud datareceiver endpoint that supports json encoding.
    """

    def __init__(self,
                 address,
                 apiKey,
                 useHTTPS=True,
                 source=None,
                 buflen=defaultMetricBufferSize,
                 pubfreq=defaultPublishFrequency):
        super(CloudPublisher, self).__init__(buflen, pubfreq)
        self._agent = Agent(reactor, NoVerificationPolicy(), pool=getPool())
        self._address = address
        self._apiKey = apiKey
        self._source = source

        scheme = 'https' if useHTTPS else 'http'
        self._url = "{scheme}://{address}/v1/data-receiver/metrics".format(
            scheme=scheme, address=address)
        self._agent_suffix = os.path.basename(sys.argv[0].rstrip(".py")) if sys.argv[0] else "python"
        reactor.addSystemEventTrigger('before', 'shutdown', self._shutdown)

    def build_metric(self, metric, value, timestamp, tags):
        metric = super(CloudPublisher, self).build_metric(metric, value, timestamp, tags)

        # TODO: Need to get this from config!
        source = 'zennub.0'

        # For internal metrics, include all tags.
        if tags.get('internal', False):
            metric['tags']['source'] = source
            return metric

        # Set the metric name correctly.
        # We want to be using datasource_datapoint naming.  In order to do this,
        # we rely upon collector daemons and their config services to make use of
        # the metricPrefix metadata field to change the formatting of the metric
        # name from <device id>/<dp id> to <ds id>/<dp_id>
        if '/' in metric['metric']:
            if 'device' in tags and metric['metric'].startswith(tags['device']):
                log.debug("Warning: metric name %s appears to start with a device id, rather than a datasource name", metric['metric'])

            metric['metric'].replace('/', '_', 1)

        metric['tags'] = {
            'source': source,
            'device': tags.get('device', ''),
            'component': tags.get('contextUUID', '')
        }

        if metric['tags']['device'] == metric['tags']['component']:
            # no need for this.
            del metric['tags']['component']

        return metric

    def _metrics_published(self, response, llen, remaining=0):
        if response.code != 200:
            raise IOError("Expected HTTP 200, but received %d from %s" % (response.code, self._url))

        log.debug("published %d metrics and received response: %s",
                  llen, response.code)
        finished = defer.Deferred()
        response.deliverBody(ResponseReceiver(finished))
        if remaining:
            reactor.callLater(0, self._putLater, False)
        return finished

    def _response_finished(self, result):
        # The most likely result is the HTTP response from a successful POST.
        if isinstance(result, str):
            log.debug("response was: %s", result)
        # We could be called back because _publish_failed was called before us
        elif isinstance(result, int):
            log.info("queue still contains %d metrics", result)
        # Or something strange could have happend
        else:
            log.warn("Unexpected result: %s", result)

    def _shutdown(self):
        log.debug('shutting down CloudPublisher [publishing %s metrics]' % len(self._mq))
        if len(self._mq):
            return self._make_request()

    def _make_request(self):
        metrics = []
        for x in xrange(BATCHSIZE):
            if not self._mq:
                break
            metrics.append(self._mq.popleft())
        if not metrics:
            log.debug('no metrics to send')
            return defer.succeed(None)

        serialized_metrics = json.dumps([metrics])
        body_writer = StringProducer(serialized_metrics)

        headers = Headers({
            'User-Agent': ['Zenoss Metric Publisher: %s' % self._agent_suffix],
            'Content-Type': ['application/json']})

        if self._apiKey:
            headers.addRawHeader('zenoss-api-key', self._apiKey)

        log.debug("Posting %s metrics" % len(metrics))
        d = self._agent.request(
            'POST', self._url, headers,
            body_writer)

        d.addCallbacks(self._metrics_published, errback=self._publish_failed,
        callbackArgs = [len(metrics), len(self._mq)], errbackArgs = [metrics])
        d.addCallbacks(self._response_finished, errback=self._publish_failed,
                       errbackArgs = [metrics])

        return d

    def _put(self, scheduled):
        """
        Push the buffer of metrics
        @param scheduled: scheduled invocation?
        """
        if scheduled:
            self._reschedule_pubtask(scheduled)

        if len(self._mq) == 0:
            return defer.succeed(0)

        log.debug('trying to publish %d metrics', len(self._mq))
        try:
            return self._make_request()
        except Exception, e:
            import pdb; pdb.set_trace()

