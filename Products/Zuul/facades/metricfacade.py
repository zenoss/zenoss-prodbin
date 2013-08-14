##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from datetime import datetime, timedelta
from zenoss.protocols.services import JsonRestServiceClient
from Products.Zuul.facades import ZuulFacade
from Products.ZenUtils.GlobalConfig import getGlobalConfiguration
from Products.ZenModel.RRDView import AGGREGATION_MAPPING
import logging
log = logging.getLogger("zen.MetricFacade")

DATE_FORMAT = "%Y/%m/%d-%H:%M:%S-%z"
METRIC_URL = getGlobalConfiguration().get('metric-url', 'http://localhost:8080')

class MetricFacade(ZuulFacade):

    def __init__(self, context):
        super(MetricFacade, self).__init__(context)
        self._client = JsonRestServiceClient(METRIC_URL)

    def getLastValue(self, context, metric):
        """
        Convience method for retrieving the last value for a metric on a context. Will return -1 if not found.
        """
        result = self.getValues(context, [metric])
        if result and metric in result:
            return result[metric]
        return -1

    def getValues(self, context, metrics, start=None, end=None,
                     format="%.2lf", extraRpn="", cf="avg"):
        """
        Return a dict of key value pairs where metric names are the keys and
        the most recent value in the given time range is the value.

        Note: all dates must be passed in in the format: strftime("%Y/%m/%d-%H:%M:%S-%z") or as an unix timestamp.

        @param context: Model object for which we are fetching metrics for
        @param dataPointIds: array of the ids of datapoints. An example would be: ['sysUpTime']
        @param start: start of the date range we are examining metrics for, defaults to now - context.defaultDateRange (defined in DataRoot.py). Does accept unix timestamps.
        @param end: end time of the date range, defaults to now. Does accept unix timestamps.
        @param format: the format we are returning the data in
        @param extraRpn: an extra rpn expression appended to the datapoint RPN expression
        @param cf: Consolidation functions, valid consolidation functions are avg, min, max, and sum
        @return: Dictionary of [dataPointId: value]
        """
        # if it is a uid look up the object
        if isinstance(context, basestring):
            context = self._getObject(context)

        results = dict()

        # build the metrics section of the query
        datapoints = []
        for ds in metrics:
            dp = next((d for d in context._getRRDDataPointsGen() if ds in d.name()), None)
            if dp is None:
                continue
            datapoints.append(self._buildMetric(dp, cf, extraRpn, format))

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
        if start is None:
            start = self._formatTime(datetime.today() - timedelta(seconds = context.defaultDateRange))

        request = self._buildRequest(context, datapoints, start, end)

        # submit it to the client
        response, content = self._client.post('query/performance', request)
        if content and content.get('results'):
           # Output of this request should be something like this:
           # [{u'timestamp': 1376477481, u'metric': u'sysUpTime',
           #   u'value': 2418182400.0, u'tags': {u'device':
           #   u'55d1bbf8-efab-4175-b585-1d748b275b2a', u'uuid':
           #   u'55d1bbf8-efab-4175-b585-1d748b275b2a', u'datasource':
           #   u'sysUpTime'}}]
           #
           for r in content['results']:
               results[r['metric']] = r['value']
        return results

    def _buildRequest(self, context, metrics, start=None, end=None):
        request = {
            'tags': self._buildTagsFromContext(context),
            'returnset': 'LAST',
            'start': start,
            'end': end,
            'metrics': metrics
            }
        return request

    def _buildTagsFromContext(self, context):
        return dict(uuid=context.getUUID())

    def _buildMetric(self, dp, cf, extraRpn="", format=""):
        # get the rpn off of the datapoint
        rpn = str(dp.rpn)
        if rpn:
            rpn = "," + rpn
        if extraRpn:
            rpn = rpn + "," + extraRpn

        # find out our aggregation function
        agg = AGGREGATION_MAPPING.get(cf.lower(), cf.lower())
        dsId, dpId = dp.name().split("_")
        return dict(
            metric=dpId,
            aggregator=agg,
            rpn=rpn,
            format=format,
            tags={'datasource': dsId}
        )

    def _formatTime(self, t):
        """
        Formats a datetime object
        @return: the date as a string.
        """
        return t.strftime(DATE_FORMAT)
