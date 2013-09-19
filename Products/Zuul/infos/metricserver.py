##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from zope.component import adapts, getMultiAdapter
from zope.interface import implements
from Products.ZenModel.DeviceComponent import DeviceComponent
from Products.Zuul.infos import ProxyProperty, HasUuidInfoMixin
from Products.Zuul.interfaces import template as templateInterfaces, IInfo
from Products.ZenModel.DataPointGraphPoint import DataPointGraphPoint
from Products.ZenModel.ThresholdGraphPoint import ThresholdGraphPoint
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.GraphDefinition import GraphDefinition
from Products.Zuul.facades.metricfacade import AGGREGATION_MAPPING
from Products.ZenModel.ConfigurationError import ConfigurationError

__doc__ = """
These adapters are responsible for serializing the graph
definitions into a form that is consumable by the metric service
"""

class MetricServiceGraph(HasUuidInfoMixin):
    def __init__(self, graph, context):
        self._object = graph
        self._context = context

class MetricServiceGraphDefinition(MetricServiceGraph):
    adapts(GraphDefinition, ZenModelRM)
    implements(templateInterfaces.IMetricServiceGraphDefinition)

    @property
    def width(self):
        return self._object.width * 2

    @property
    def height(self):
        return 500

    @property
    def title(self):
        return self._object.titleOrId()

    @property
    def contextTitle(self):
        """
        For the reports we need the context in the title.
        """
        title = self._context.device().deviceClass().getOrganizerName() + "/" + self._context.device().titleOrId()
        if isinstance(self._context, DeviceComponent):
            title =  "%s - %s" %(title, self._context.name())
        return "%s - %s" % (self.title, title)

    @property
    def type(self):
        # previously the type was stored on the datapoint
        # and now it is a property of the graph. Graph the first graphdef
        # type and just use that for now.
        datapoints = self.datapoints
        if len(datapoints):
            return datapoints[0].type

    def _getGraphPoints(self, klass):
        graphDefs = self._object.getGraphPoints(True)
        infos = [getMultiAdapter((g, self._context), templateInterfaces.IMetricServiceGraphPoint)
                 for g in graphDefs if isinstance(g, klass) ]
        return infos

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
        return o.talesEval(o.legend, self._context)

    @property
    def color(self):
        return self._object.getColor(self._object.sequence)


class MetricServiceThreshold(ColorMetricServiceGraphPoint):
    adapts(ThresholdGraphPoint, ZenModelRM)
    implements(templateInterfaces.IMetricServiceGraphPoint)
    @property
    def values(self):
        """
        Return the values we wish to display for this threshold.
        """
        cls = self._object.getThreshClass(self._context)
        relatedGps = self._object.getRelatedGraphPoints(self._context)
        if cls:
            instance = cls.createThresholdInstance(self._context)
            # filter out the None's
            return [x for x in instance.getGraphValues(relatedGps) if x is not None]
        return []

class MetricServiceGraphPoint(ColorMetricServiceGraphPoint):
    adapts(DataPointGraphPoint, ZenModelRM)
    implements(templateInterfaces.IMetricServiceGraphPoint)
    @property
    def id(self):
        return self._object.id
    
    @property
    def name(self):
        return "%s %s" % (self._context.id,self._object.id)

    @property
    def metric(self):
        return self._object.dataPointId()

    @property
    def type(self):
        return self._object.lineType.lower()

    def _getDataPoint(self):
        try:
            return IInfo(self._object.graphDef().rrdTemplate().getRRDDataPoint(self._object.dpName))
        except (ConfigurationError, AttributeError):
            return None

    @property
    def rate(self):
        datapoint = self._getDataPoint()
        if datapoint:
            return datapoint.rate
        return False

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
        return {'datasource': [self._object.dpName.split("_")[0]], 'uuid': [self._context.getUUID()]}

    @property
    def format(self):
        fmt = self._object.format
        if fmt:
            # RRD had an lf that meant the same thing as %f so just drop the l
            # the "s" means scale it to the appropiate units. This maybe something
            # we need to replicate later
            # also sometimes we had a %% which means to display a literal percent.
            return fmt.replace("l", "").replace("%s", "").rstrip("%")

    @property
    def expression(self):
        rpn = self._object.rpn
        if rpn:
            return "rpn:" + self._object.talesEval(rpn, self._context)

# Charts adapters for collector graphs
class CollectorMetricServiceGraphDefinition(MetricServiceGraphDefinition):
    adapts(GraphDefinition, PerformanceConf)
    implements(templateInterfaces.IMetricServiceGraphDefinition)

    def __init__(self, graphDef, context):
        self._object = graphDef
        self._context = context

    @property
    def tags(self):
        return dict(monitor=[self._context.id])

    @property
    def contextTitle(self):
        return "%s - %s" % (self.title, self._context.titleOrId())

class CollectorDataPointGraphPoint(MetricServiceGraphPoint):
    adapts(DataPointGraphPoint, PerformanceConf)
    implements(templateInterfaces.IMetricServiceGraphPoint)
    @property
    def tags(self):
        return {'daemon': [self._object.dpName.split("_")[0]]}


class MultiContextMetricServiceGraphDefinition(MetricServiceGraphDefinition):
    """
    This is a specialized adapter for multi graph reports where we have metrics for multiple
    contexts on a single adapter. 
    """
    implements(templateInterfaces.IMetricServiceGraphDefinition)

    @property
    def contextTitle(self):
        pass

    def _getGraphPoints(self, klass):
        """
        For each context we have we need a new datapoint. 
        """
        graphDefs = self._object.getGraphPoints(True)
        infos = []
        for context in self._context:
            infos.extend([getMultiAdapter((g, context), templateInterfaces.IMetricServiceGraphPoint)
                          for g in graphDefs if isinstance(g, klass) ])
        return infos

