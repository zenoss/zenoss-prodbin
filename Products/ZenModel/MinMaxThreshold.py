import rrdtool
from AccessControl import Permissions

from Globals import InitializeClass
from ThresholdClass import ThresholdClass
from ThresholdInstance import ThresholdInstance, ThresholdContext
from Products.ZenModel.PerformanceConf import performancePath
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Perf_Snmp, Clear
from Products.ZenUtils.ZenTales import talesEval

import logging
log = logging.getLogger('zen.MinMaxCheck')

from sets import Set

class MinMaxThreshold(ThresholdClass):
    
    minval = ""
    maxval = ""
    eventClass = Perf_Snmp
    severity = 3
    escalateCount = 0
    
    _properties = ThresholdClass._properties + (
        {'id':'minval',        'type':'string',  'mode':'w'},
        {'id':'maxval',        'type':'string',  'mode':'w'},
        {'id':'eventClass',    'type':'string',  'mode':'w'},
        {'id':'severity',      'type':'int',     'mode':'w'},
        {'id':'escalateCount', 'type':'int',     'mode':'w'},
        )

    factory_type_information = (
        { 
        'immediate_view' : 'editRRDThreshold',
        'actions'        :
        ( 
        { 'id'            : 'edit'
          , 'name'          : 'Min/Max Threshold'
          , 'action'        : 'editRRDThreshold'
          , 'permissions'   : ( Permissions.view, )
          },
        )
        },
        )

    def createThresholdInstance(self, context):
        """Return the config used by the collector to process simple min/max
        thresholds. (id, minval, maxval, severity, escalateCount)
        """
        mmt = MinMaxThresholdInstance(self.id,
                                      ThresholdContext(context),
                                      self.dsnames,
                                      minval=self.getMinval(context),
                                      maxval=self.getMaxval(context),
                                      eventClass=self.eventClass,
                                      severity=self.severity,
                                      escalateCount=self.escalateCount)
        return mmt

    def getMinval(self, context):
        """Build the min value for this threshold.
        """
        minval = None
        if self.minval:
            minval = talesEval("python:"+self.minval, context)
        return minval


    def getMaxval(self, context):
        """Build the max value for this threshold.
        """
        maxval = None
        if self.maxval:
            maxval = talesEval("python:"+self.maxval, context)
        return maxval

InitializeClass(MinMaxThreshold)
MinMaxThresholdClass = MinMaxThreshold

class MinMaxThresholdInstance(ThresholdInstance):
    
    def __init__(self, id, context, dpNames,
                 minval, maxval, eventClass, severity, escalateCount):
        self._context = context
        self.id = id
        self.minimum = minval
        self.maximum = maxval
        self.eventClass = eventClass
        self.severity = severity
        self.escalateCount = escalateCount
        self.dataPointNames = dpNames
        self._rrdInfoCache = {}

    def name(self):
        "return the name of this threshold (from the ThresholdClass)"
        return self.id

    def context(self):
        "Return an identifying context (device, or device and component)"
        return self._context

    def dataPoints(self):
        "Returns the names of the datapoints used to compute the threshold"
        return self.dataPointNames

    def rrdInfoCache(self, dp):
        if dp in self._rrdInfoCache:
            return self._rrdInfoCache[dp]
        data = rrdtool.info(self.context().path(dp))
        value = data['step'], data['ds']['ds0']['type']
        self._rrdInfoCache[dp] = value
        return value

    def check(self, dataPoints):
        """The given datapoints have been updated, so re-evaluate.
        returns events or an empty sequence"""
        result = []
        for dp in self.dataPointNames:
            cycleTime, rrdType = self.rrdInfoCache(dp)
            startStop, names, values = \
                       rrdtool.fetch(self.context().path(dp), 'AVERAGE',
                                     '-s', 'now-%d' % (cycleTime*2),
                                     '-e', 'now')
            value = values[0][0]
            result.extend(self.checkRange(dp, value))
        return result

    def checkRaw(self, dataPoint, timeOf, value):
        """A new datapoint has been collected, use the given _raw_
        value to re-evalue the threshold."""
        result = []
        cycleTime, rrdType = self.rrdInfoCache(dataPoint)
        if rrdType != 'GAUGE':
            startStop, names, values = \
                       rrdtool.fetch(self.context().path(dataPoint), 'AVERAGE',
                                     '-s', 'now-%d' % (cycleTime*2),
                                     '-e', 'now')
            value = values[0][0]
        result.extend(self.checkRange(dataPoint, value))
        return result

    def checkRange(self, dp, value):
        'Check the value for min/max thresholds'
        log.debug("Checking %s %s against min %s and max %s",
                  dp, value, self.minimum, self.maximum)
        if value is None:
            return []
        thresh = None
        if self.maximum is not None and value > self.maximum:
            thresh = self.maximum
            how = 'exceeded'
        if self.minimum is not None and value < self.minimum:
            thresh = self.minimum
            how = 'not met'
        label = self.context().componentName or ''
        if thresh is not None:
            self.count = (self.count or 0) + 1
            severity = self.severity
            if self.escalateCount and self.count >= self.escalateCount:
                severity += 1
            summary = '%s %s threshold of %s %s: current value %.2f' % (
                self.context().deviceName, label, self.name(), how, float(value))
            return [dict(device=self.context().deviceName,
                         summary=summary,
                         eventClass=self.eventClass,
                         component=self.context().componentName,
                         severity=severity)]
        else:
            if self.count or self.count is None:
                summary = '%s %s threshold restored current value: %.2f' % (
                    self.context().deviceName, label, value)
                self.count = 0
                return [dict(device=self.context().deviceName,
                             summary=summary,
                             eventClass=self.eventClass,
                             component=self.context().componentName,
                             severity=Event.Clear)]
        return []

    def getGraphElements(self, template, gopts, namespace, color):
        """Produce a visual indication on the graph of where the
        threshold applies."""
        ns = namespace
        n = self.minimum
        x = self.maximum
        path = self.context().path(self.dataPointNames[0])
        apoint = template.getRRDDataPoint(self.dataPointNames[0])
        rpn = ''
        if apoint.rpn:
            rpn = "," + apoint.rpn
        result = []
        adef = ns + 'ds0'
        if n:
            result += [
                "DEF:n%s=%s:ds0:AVERAGE" % (adef, path),
                "CDEF:cn%s=n%s,UN,%s,%s,IF%s" % (adef, adef, n, n, rpn),
                "LINE1:cn%s%s:%s\\j" % (adef, color, self.getMinLabel()),
                ]
        if x:
            result += [
                "DEF:x%s=%s:ds0:AVERAGE" % (adef, path),
                "CDEF:cx%s=x%s,UN,%s,%s,IF%s" % (adef, adef, x, x, rpn),
                "LINE1:cx%s%s:%s\\j" % (adef, color, self.getMaxLabel())
            ]
        return gopts + result


    def getMinLabel(self):
        """build a label for a min threshold"""
        return "%s < %s" % (self.getNames(), self.setPower(self.minimum))


    def getMaxLabel(self):
        """build a label for a max threshold"""
        return "%s > %s" % (self.getNames(),self.setPower(self.maximum))

    def getNames(self):
        names = list(Set([x.split('_', 1)[1] for x in self.dataPointNames]))
        names.sort()
        return ', '.join(names)


    def setPower(self, number):
        powers = ("k", "M", "G")
        if number < 1000: return number
        for power in powers:
            number = number / 1000
            if number < 1000:  
                return "%0.2f%s" % (number, power)
        return "%.2f%s" % (number, powers[-1])

from twisted.spread import pb
pb.setUnjellyableForClass(MinMaxThresholdInstance, MinMaxThresholdInstance)
