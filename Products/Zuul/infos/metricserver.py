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
from Products.ZenModel.TrendlineThreshold import TrendlineThreshold
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.PerformanceConf import PerformanceConf
from Products.ZenModel.GraphDefinition import GraphDefinition
from Products.ZenModel.ComplexGraphPoint import ComplexGraphPoint
from Products.ZenModel.ConfigurationError import ConfigurationError
from Products.ZenEvents.Exceptions import rpnThresholdException
from Products.ZenUtils import metrics
from Products.Zuul.decorators import info

__doc__ = """
These adapters are responsible for serializing the graph
definitions into a form that is consumable by the metric service
"""

class MetricServiceGraph(HasUuidInfoMixin):
    def __init__(self, graph, context):
        self._object = graph
        self._context = context
        self._showContextTitle = False

class MetricServiceGraphDefinition(MetricServiceGraph):
    adapts(GraphDefinition, ZenModelRM)
    implements(templateInterfaces.IMetricServiceGraphDefinition)

    @property
    def title(self):
        obj = self._object
        # allow zenpacks to set a temporary title on the graph definition
        if hasattr(obj, "_v_title"):
            return obj._v_title
        if self._showContextTitle:
            return self.contextTitle
        return self._object.titleOrId()

    @property
    def contextTitle(self):
        """
        For the reports we need the context in the title.
        """
        title = self._context.device().deviceClass().getOrganizerName() + "/" + self._context.device().titleOrId()
        if isinstance(self._context, DeviceComponent):
            title =  "%s - %s" %(title, self._context.titleOrId())
        return "%s - %s" % (self._object.titleOrId(), title)

    @property
    def type(self):
        return "line"

    def _getGraphPoints(self, klass):
        graphDefs = self._object.getGraphPoints(True)
        infos = [getMultiAdapter((g, self._context), templateInterfaces.IMetricServiceGraphPoint)
                 for g in graphDefs if isinstance(g, klass) ]
        return infos

    @property
    def datapoints(self):
        # make sure the sequence always makes sense. This will prevent graphs from all having the same color
        self._object.manage_resequenceGraphPoints()
        return self._getGraphPoints(DataPointGraphPoint)

    @property
    def thresholds(self):
        return self._getGraphPoints(ThresholdGraphPoint)

    @property
    @info
    def projections(self):
        """
        Return all TrendlineThresholds as info objects
        """
        thresholdGraphPoints = self._getGraphPoints(ThresholdGraphPoint)
        projections = []
        for gp in thresholdGraphPoints:
            tclass = gp._object.getThreshClass(self._context)
            if isinstance(tclass, TrendlineThreshold):
                projections.append(tclass)
        return projections

    @property
    def base(self):
        if self._object.base:
            return 1024
        return 1000

    @property
    def autoscale(self):
        return self._object.shouldAutoScale()

    @property
    def ceiling(self):
        return self._object.getCeiling()

    @property
    def description(self):
        return self._object.getDescription()

    miny = ProxyProperty('miny')
    maxy = ProxyProperty('maxy')
    units = ProxyProperty('units')


class ColorMetricServiceGraphPoint(MetricServiceGraph):

    def __init__(self, graph, context):
        self._multiContext = False
        super(ColorMetricServiceGraphPoint, self).__init__(graph, context)

    def setMultiContext(self):
        """
        Let this graph know that we are displaying the same
        metric for multiple contexts. This means we have to be
        more specific in our legend and we can not have repeating
        colors.
        """
        self._multiContext = True

    @property
    def legend(self):
        o = self._object
        legend = o.talesEval(o.legend, self._context)
        if self._multiContext:
            legend = self._context.titleOrId() + " " + legend
        return legend

    @property
    def color(self):
        if not self._multiContext:
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
            try:
                return [x for x in instance.getGraphValues(relatedGps, self._context) if x is not None]
            except rpnThresholdException:
                # the exception is logged by the threshold instance class
                pass
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
        return metrics.ensure_prefix(self._context.device().id,
                self._object.dpName)

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
            options = datapoint.getRateOptions()
            if datapoint._object.isCounter() and int(self._object.limit) > 0:
                options['resetThreshold'] = self._object.limit
            return options

    @property
    def aggregator(self):
        agg = self._object.cFunc.lower()
        from Products.Zuul.facades.metricfacade import AGGREGATION_MAPPING
        return AGGREGATION_MAPPING.get(agg, agg)

    @property
    def tags(self):
        metadata = self._context.getMetricMetadata()
        return {'key': [metadata.get('contextKey')]}

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
    def emit(self):
        if self._object.lineType == ComplexGraphPoint.LINETYPE_DONTDRAW:
            return False
        return True

    @property
    def expression(self):
        rpn = self._object.rpn
        if rpn:
            return "rpn:" + self._object.talesEval(rpn, self._context)

    @property
    def fill(self):
        if self.type == "area":
            return True
        return False

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
    def metric(self):
        return self._object.dpName.split("_")[1]

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
            for info in infos:
                info.setMultiContext()
        return infos
