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


METRIC_URL = getGlobalConfiguration().get('metric-url', 'http://localhost:8080')

class MetricFacade(ZuulFacade):

    def __init__(self, context):
        super(MetricFacade, self).__init__(context)
        self._client = JsonRestServiceClient(METRIC_URL)

    def getLastValue(self, context, metrics):
        log.info("Getting metrics %s on context %s", metrics, context)
        start = self._formatTime(datetime.today() - timedelta(hours = 1))
        end = self._formatTime(datetime.today())
        result = self.getValue(context, metrics, start=start,
                             end=end)
        if result:
            result['results'].reverse()
            if len(result['results']):
                return result['results'][0]['value']
        return None

    def getValue(self, context, metrics, start=None, end=None,
                     format="%.2lf", extraRpn="", cf="avg"):
        request = self._buildRequest(context, metrics, start, end, format, extraRpn, cf)
        # submit it to the client
        response, result = self._client.post('query/performance', request)
        return result

    def _buildRequest(self, context, metrics, start=None, end=None,
                      format="%.2lf", extraRpn="", cf="AVERAGE"):
        agg = AGGREGATION_MAPPING.get(cf.lower(), cf.lower())
        # build the json definition
        request = {
            'tags': self._buildTagsFromContext(context),
            'resultset': 'LAST',
            'start': start,
            'end': end,
            'metrics': self._buildMetrics(metrics, agg, extraRpn, format),
            }
        return request

    def _buildTagsFromContext(self, context):
        return dict(uuid=context.getUUID())

    def _buildMetrics(self, metrics, cf, extraRpn="", format=""):
        if isinstance(metrics, basestring):
            metrics = [metrics]
        result = []
        for metric in metrics:
            ds, dp = metric.split("_")
            result.append(dict(
                    metric=dp,
                    aggregator=cf,
                    rpn=extraRpn,
                    format=format,
                    tags={'datasource': ds}
            ))
        return result

    def _formatTime(self, t):
        return t.strftime("%Y/%m/%d-%H:%M:%S-%z")
