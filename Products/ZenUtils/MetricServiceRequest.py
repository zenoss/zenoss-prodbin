##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import base64
import json

SEPARATOR_CHAR = "/"

from StringIO import StringIO
from cookielib import CookieJar
from twisted.internet import reactor
from twisted.web.client import Agent, CookieAgent, FileBodyProducer, readBody
from twisted.web.http_headers import Headers
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenUtils.metrics import ensure_prefix
from Products.Zuul.facades.metricfacade import METRIC_URL_PATH, AGGREGATION_MAPPING
from Products.Zuul.interfaces import IAuthorizationTool
import logging

log = logging.getLogger('zen.metrics')

class MetricServiceRequest(object):
    """
    A convience class for fetching metrics from CentralQuery that can
    be used by twisted daemons.
    """
    # use a shared cookie jar so all Metric requests can share the same session
    cookieJar = CookieJar()

    def __init__(self, userAgent):
        self._aggMapping = AGGREGATION_MAPPING
        urlstart = getGlobalConfiguration().get('metric-url', 'http://localhost:8080')
        self._metric_url = '%s/%s' % (urlstart, METRIC_URL_PATH)
        creds = IAuthorizationTool(None).extractGlobalConfCredentials()
        auth = base64.b64encode('{login}:{password}'.format(**creds))
        self.agent = CookieAgent(Agent(reactor, connectTimeout=30), self.cookieJar)
        self._headers = Headers({
            'Authorization': ['basic %s' % auth],
            'content-type': ['application/json'],
            'User-Agent': ['Zenoss: %s' % userAgent]
        })
        self.onMetricsFetched = None

    def setMetricHandler(self, fn):
        self.onMetricsFetched = fn

    def getMetrics(self, uuid, dpNames, cf='AVERAGE', rate=False, downsample="1h-avg", start=None, end=None, deviceId=None, returnSet="EXACT"):
        metrics = []
        if isinstance(dpNames, basestring):
            dpNames = [dpNames]
        for dpName in dpNames:
            name = ensure_prefix(deviceId, dpName)
            metrics.append(dict(
                metric=name,
                aggregator=self._aggMapping.get(cf.lower(), cf.lower()),
                rpn='',
                rate=rate,
                format='%.2lf',
                tags=dict(contextUUID=[uuid]),
                name='%s_%s' % (uuid, dpName)
            ))

        request = dict(
            returnset=returnSet,
            start=start,
            end=end,
            downsample=downsample,
            metrics=metrics
        )
        body = FileBodyProducer(StringIO(json.dumps(request)))
        d = self.agent.request('POST', self._metric_url, self._headers, body)
        d.addCallbacks(self.handleMetricResponse, self.onError)
        return d

    def onError(self, reason):
        log.warn("Unable to fetch metrics from central query %s", reason)

    def handleMetricResponse(self, response):
        d = readBody(response)
        if response.code > 199 and response.code < 300:
            d.addCallback(self.onMetricsFetched)
        else:
            d.addCallback(self.onError)
