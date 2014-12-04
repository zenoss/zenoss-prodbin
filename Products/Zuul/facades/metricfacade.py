##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
import base64
import requests
import json
import re
import cookielib

from collections import defaultdict
from datetime import datetime, timedelta
from zope import component
from zenoss.protocols.services import ServiceResponseError, ServiceConnectionError
from Products.Zuul.facades import ZuulFacade
from Products.Zuul.interfaces import IInfo
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.Five.browser import BrowserView
from Products.Zuul.interfaces import IAuthorizationTool
from Products.Zuul.utils import safe_hasattr
from Products.ZenUtils import metrics

log = logging.getLogger("zen.MetricFacade")


DATE_FORMAT = "%Y/%m/%d-%H:%M:%S-%z"

METRIC_URL_PATH = "/api/performance/query"

AGGREGATION_MAPPING = {
    'average': 'avg',
    'minimum': 'min',
    'maximum': 'max',
    'total': 'sum',
    #TODO: get last agg function working
    'last': None
}

_devname_pattern = re.compile('Devices/([^/]+)')

def _isRunningFromUI( context):
    if not safe_hasattr( context, 'REQUEST'):
        return False

    return safe_hasattr( context.REQUEST, 'SESSION')

class MetricFacade(ZuulFacade):

    def __init__(self, context):
        super(MetricFacade, self).__init__(context)
        self._metric_url = getGlobalConfiguration().get('metric-url', 'http://localhost:8080/')

        self._cookies = cookielib.CookieJar()
        self._authorization = IAuthorizationTool( self.context)
        if _isRunningFromUI( context):
            self._credentials = self._authorization.extractCredentials( context.REQUEST)
        else:
            self._credentials = self._authorization.extractGlobalConfCredentials()

    def getLastValue(self, context, metric):
        """
        Convenience method for retrieving the last value for a metric on a context. Will return -1 if not found.
        """
        result = self.getValues(context, [metric])
        if result and metric in result:
            return result[metric]
        return -1

    def getMultiValues(self, contexts, metrics, start=None, end=None, returnSet="LAST", downsample=None):
        """
        Use this method when you need one or more metrics on multiple contexts.

        Returns all the values for the given contexts and the given metrics over the date range specified by start to end
        @param contexts: array of either uids or model objects
        @param metrics: name of metrics (datapoints).
        @param start: defaults to now - dmd.defaultDateRange can be either a timestamp or a string in DATE_FORMAT format
        @param end: defaults to now, can be either a timestamp or a string in DATE_FORMAT format
        @param returnSet: default "LAST" (which returns the last value) the other options are ALL which returns everthing, and EXACT which returns what is in the date range
        @param downsample: can be either the string of the form 1m-avg or a number which will be assumed to be seconds averaged
        If the returnSet is EXACT or ALL, then you are returned metrics in this form:
        {
            # context UUID
            '55d1bbf8-efab-4175-b585-1d748b275b2a': {
                # metric id, is a list of timestamp and values
                'sysUpTime': [{timestamp=1234567, value=1}, {timestamp=1234568, value=2}]
                'laLoadInt5': [{timestamp=1234567, value=100}, {timestamp=1234568, value=200}]
            }

        }
        If the returnSet is LAST then you get the results of the form
        {
            '55d1bbf8-efab-4175-b585-1d748b275b2a': {
                'sysUpTime': 2
                'laLoadInt5': 4
            }

        }
        """
        results = {}
        data = self.queryServer(contexts, metrics, start=start, end=end, returnSet=returnSet, downsample=downsample)
        if returnSet == "LAST":
            return data
        # if the returnSet is exact or all then organize the results into something more digestable
        for row in data:
            key, metric = row['metric'].split('|', 1)
            if not results.get(key):
                results[key] = defaultdict(list)
            for dp in row.get('datapoints', []):
                if not dp['value'] is None and dp['value'] != u'NaN':
                    results[key][metric].append(dict(timestamp=dp['timestamp'], value=dp['value']))
        return results

    def getValues(self, context, metrics, start=None, end=None,
                     format="%.2lf", extraRpn="", cf="avg", returnSet="LAST", downsample=None):
        """
        Return a dict of key value pairs where metric names are the keys and
        the most recent value in the given time range is the value.

        Note: all dates must be passed in in the format: strftime("%Y/%m/%d-%H:%M:%S-%z") or as an unix timestamp.

        Use this method when you need to get one or more metrics for a single context.

        @param context: One or more model object for which we are fetching metrics for
        @param dataPointIds: array of the ids of datapoints. An example would be: ['sysUpTime']
        @param start: start of the date range we are examining metrics for, defaults to now - context.defaultDateRange (defined in DataRoot.py). Does accept unix timestamps.
        @param end: end time of the date range, defaults to now. Does accept unix timestamps.
        @param format: the format we are returning the data in
        @param extraRpn: an extra rpn expression appended to the datapoint RPN expression
        @param cf: Consolidation functions, valid consolidation functions are avg, min, max, and sum
        @param returnSet: default "LAST" (which returns the last value) the other options are ALL which returns everthing, and EXACT which returns what is in the date range
        @param downsample: can be either the string of the form 1m-avg or a number which will be assumed to be seconds averaged
        @return: Dictionary of [dataPointId: value]
        """
        results = self.queryServer(context, metrics, start=start, end=end, format=format, extraRpn=extraRpn, cf=cf, returnSet=returnSet, downsample=downsample)
        if len(results.values()):
            return results.values()[0]
        return {}

    def queryServer(self, contexts, metrics, start=None, end=None,
                     format="%.2lf", extraRpn="", cf="avg", returnSet="LAST", downsample=None):
        subjects = []
        # make sure we are always dealing with a list
        if not isinstance(contexts, (list, tuple)):
            contexts = [contexts]

        for context in contexts:
            if isinstance(context, basestring):
                subjects.append(self._getObject(context))
            else:
                subjects.append(context)

        # build the metrics section of the query
        datapoints = []
        metricnames = {}
        for ds in metrics:
            # find the first occurrence of a datapoint on a context.
            # in theory it is possible that a passed in metric exists on one context
            # but not another.
            for subject in subjects:
                dp = next((d for d in subject._getRRDDataPointsGen() if ds in d.name() ), None)
                if dp is None:
                    continue
                else:
                    # we have found a definition for a datapoint, use it and continue onp
                    metricnames[dp.name()] = ds
                    for subject in subjects:
                        datapoints.append(self._buildMetric(subject, dp, cf, extraRpn, format))
                    break

        # no valid datapoint names were entered
        if not datapoints:
            return {}

        # check to see if the user entered a unix timestamp
        if isinstance(start, (int, long, float)):
            start = self._formatTime(datetime.fromtimestamp(start))

        if isinstance(end, (int, long, float)):
            end = self._formatTime(datetime.fromtimestamp(end))

        # if no start time or end time specified use the
        # defaultDateRange (which is acquired from the dmd)
        if end is None:
            end = self._formatTime(datetime.today())
        if start is None and returnSet != "LAST":
            start = self._formatTime(datetime.today() - timedelta(seconds = self._dmd.defaultDateRange))
        elif start is None and returnSet == "LAST":
            start = self._formatTime(datetime.today() - timedelta(seconds = 3600))
        request = self._buildRequest(subjects, datapoints, start, end, returnSet, downsample)

        # submit it to the client
        try:
            response = self._post_request( self._uri(METRIC_URL_PATH), request)
            content = response.json()
        except ServiceResponseError, e:
            # there was an error returned by the metric service, log it here
            log.error("Error fetching request: %s \nResponse from the server: %s", request, e.content)
            return {}
        except ServiceConnectionError, e:
            log.error("Error connecting with request: %s \n%s", request, e )
            return {}


        if content and content.get('results') is not None and returnSet=="LAST":
           # Output of this request should be something like this:
           # [{u'timestamp': 1376477481, u'metric': u'sysUpTime',
           #   u'value': 2418182400.0, u'tags': {u'device':
           #   u'55d1bbf8-efab-4175-b585-1d748b275b2a', u'uuid':
           #   u'55d1bbf8-efab-4175-b585-1d748b275b2a', u'datasource':
           #   u'sysUpTime'}}]
           #
           results = defaultdict(dict)
           for item in content['results']:
               key, metric = item['metric'].split('|', 1)
               if item.get('datapoints'):
                   results[key][metricnames[metric]] = float(format % item['datapoints'][0]['value'])
           return results
        else:
           if returnSet == "ALL":
               return content
           return content.get('results')

    def _buildRequest(self, contexts, metrics, start, end, returnSet, downsample):
        request = {
            'returnset': returnSet,
            'start': start,
            'end': end,
            'metrics': metrics
        }
        if not downsample is None:
            if isinstance(downsample, int):
                request['downsample'] = "%s-avg" % downsample
            else:
                request['downsample'] = downsample
        return request

    def _buildTagsFromContextAndMetric(self, context, dsId):
        return dict(key=[context.getResourceKey()])

    def _get_key_from_tags(self, tags):
        key = tags.get('key', '')
        if isinstance(key, (list, set, tuple)):
            key = key[0]
        return key

    def _buildMetric(self, context, dp, cf, extraRpn="", format=""):
        datasource = dp.datasource()
        dsId = datasource.id
        info = IInfo(dp)

        # find out our aggregation function
        agg = AGGREGATION_MAPPING.get(cf.lower(), cf.lower())
        rateOptions = info.getRateOptions()
        tags = self._buildTagsFromContextAndMetric(context, dsId)
        metricname = dp.name()
        key = self._get_key_from_tags(tags)
        search = _devname_pattern.match(key)
        if search:
            prefix = search.groups()[0]
            metricname = metrics.ensure_prefix(prefix, metricname)
        metric = dict(
            metric=metricname,
            aggregator=agg,
            rpn=extraRpn,
            format=format,
            tags=tags,
            rate=info.rate,
            name=context.getResourceKey() + "|" + dp.name()
        )
        if rateOptions:
            metric['rateOptions'] = rateOptions
        return metric

    def _formatTime(self, t):
        """
        Formats a datetime object
        @return: the date as a string.
        """
        return t.strftime(DATE_FORMAT)

    def _uri(self, path):
        return "%s/%s" %( self._metric_url, path)

    def _post_request(self, path, request, timeout=10):
        uri = self._uri(METRIC_URL_PATH)
        login = self._credentials['login']
        password = self._credentials['password']
        auth = base64.b64encode('%s:%s' % (login, password))
        headers = {
            'Authorization': 'basic %s' % auth,
            'content-type': 'application/json'
        }
        try:
            response = requests.post(uri, json.dumps(request), headers=headers,
                                     timeout=timeout, cookies=self._cookies)
        except requests.exceptions.Timeout, e:
            raise ServiceConnectionError('Timed out waiting for response from metric service: %s' % e, e)
        status_code = response.status_code
        if not (status_code >= 200 and status_code <= 299):
            raise ServiceResponseError(response.reason, status_code, request, response, response.content)
        return response
