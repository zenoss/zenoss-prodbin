##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from zope.interface import implements
from Products.Zuul.infos import ProxyProperty, HasUuidInfoMixin
from Products.Zuul.interfaces import template as templateInterfaces, IInfo
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint
from Products.ZenModel.ThresholdGraphPoint import ThresholdGraphPoint
from Products.Zuul.facades.metricfacade import AGGREGATION_MAPPING
from Products.ZenModel.ConfigurationError import ConfigurationError

__doc__ = """
These adapters are responsible for serializing the graph
definitions into a form that is consumable by the metric service
"""

class MetricServiceGraph(HasUuidInfoMixin):
    implements(templateInterfaces.IMetricServiceGraphDefinition)

    def __init__(self, graph):
        self._object = graph


class MetricServiceGraphDefinition(MetricServiceGraph):
    def setContext(self, context):
        self._context = context

    @property
    def width(self):
        return self._object.width * 2

    @property
    def height(self):
        return self._object.height * 3

    @property
    def title(self):
        return self._object.titleOrId()

    @property
    def type(self):
        # previously the type was stored on the datapoint
        # and now it is a property of the graph. Graph the first graphdef
        # type and just use that for now.
        datapoints = self.datapoints
        if len(datapoints):
            return datapoints[0].type

    @property
    def tags(self):
        # TODO: possibly create a new adapter so zenpacks can register their own metric service tags
        return { 'uuid': [self._context.getUUID()] }

    def _getGraphPoints(self, klass):
        graphDefs = self._object.getGraphPoints(True)
        return [templateInterfaces.IMetricServiceGraphDefinition(g) for g in graphDefs if isinstance(g, klass) ]

    @property
    def datapoints(self):
        return self._getGraphPoints(DataPointGraphPoint)

    @property
    def thresholds(self):
        return self._getGraphPoints(ThresholdGraphPoint)

    base = ProxyProperty('base')
    miny = ProxyProperty('miny')
    maxy = ProxyProperty('maxy')
    units = ProxyProperty('units')

class ColorMetricServiceGraphPoint(MetricServiceGraph):
    @property
    def legend(self):
        o = self._object
        return o.talesEval(o.legend, None)

    @property
    def color(self):
        return self._object.getColor(self._object.sequence)


class MetricServiceThreshold(ColorMetricServiceGraphPoint):
    pass

class MetricServiceGraphPoint(ColorMetricServiceGraphPoint):

    @property
    def id(self):
        return self._object.id

    @property
    def metric(self):
        return self._object.dataPointId()

    @property
    def type(self):
        return self._object.lineType.lower()

    def _getDataPoint(self):
        try:
            return IInfo(self._object.graphDef().rrdTemplate().getRRDDataPoint(self._object.dpName))
        except ConfigurationError:
            return None

    @property
    def rate(self):
        datapoint = self._getDataPoint()
        if datapoint:
            return datapoint.rate

    @property
    def rateOptions(self):
        datapoint = self._getDataPoint()
        if datapoint:
            return datapoint.getRateOptions()

    @property
    def aggregator(self):
        agg = self._object.cFunc.lower()
        return AGGREGATION_MAPPING.get(agg, agg)

    @property
    def tags(self):
        return {'datasource': [self._object.dpName.split("_")[0]]}
    format = ProxyProperty('format')
    rpn = ProxyProperty('rpn')
