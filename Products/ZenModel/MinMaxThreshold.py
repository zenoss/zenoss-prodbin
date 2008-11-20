###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

__doc__= """MinMaxThreshold
Make threshold comparisons dynamic by using TALES expresssions,
rather than just number bounds checking.
"""

import rrdtool
from AccessControl import Permissions

from Globals import InitializeClass
from ThresholdClass import ThresholdClass
from ThresholdInstance import ThresholdInstance, ThresholdContext
from Products.ZenEvents import Event
from Products.ZenEvents.ZenEventClasses import Perf_Snmp
from Products.ZenUtils.ZenTales import talesEval, talesEvalStr
from Products.ZenEvents.Exceptions import pythonThresholdException, \
        rpnThresholdException

import logging
log = logging.getLogger('zen.MinMaxCheck')

from sets import Set
from Products.ZenUtils.Utils import unused
import types


def rpneval(value, rpn):
    """
    Simulate RPN evaluation: only handles simple arithmetic
    """
    if value is None: return value
    operators = ('+','-','*','/')
    rpn = rpn.split(',')
    rpn.reverse()
    stack = [value]
    while rpn:
        next = rpn.pop()
        if next in operators:
            first = stack.pop()
            second = stack.pop()
            try:
                value = eval('%s %s %s' % (second, next, first))
            except ZeroDivisionError:
                value = 0
            stack.append(value)
        elif next.upper() == 'ABS':
            stack.append(abs(float(stack.pop())))            
        else:
            stack.append(float(next))
    return stack[0]


class MinMaxThreshold(ThresholdClass):
    """
    Threshold class that can evaluate RPNs and Python expressions
    """
    
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
        """Return the config used by the collector to process min/max
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
            try:
                minval = talesEval("python:"+self.minval, context)
            except:
                msg= "User-supplied Python expression (%s) for minimum value caused error: %s" % \
                           ( self.minval,  self.dsnames )
                log.error( msg )
                raise pythonThresholdException(msg)
                minval = None
        return minval


    def getMaxval(self, context):
        """Build the max value for this threshold.
        """
        maxval = None
        if self.maxval:
            try:
                maxval = talesEval("python:"+self.maxval, context)
            except:
                msg= "User-supplied Python expression (%s) for maximum value caused error: %s" % \
                           ( self.maxval,  self.dsnames )
                log.error( msg )
                raise pythonThresholdException(msg)
                maxval = None
        return maxval

InitializeClass(MinMaxThreshold)
MinMaxThresholdClass = MinMaxThreshold



class MinMaxThresholdInstance(ThresholdInstance):
    # Not strictly necessary, but helps when restoring instances from
    # pickle files that were not constructed with a count member.
    count = {}
    
    def __init__(self, id, context, dpNames,
                 minval, maxval, eventClass, severity, escalateCount):
        self.count = {}
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

    def countKey(self, dp):
        return(':'.join(self.context().key()) + ':' + dp)
        
    def getCount(self, dp):
        countKey = self.countKey(dp)
        if not self.count.has_key(countKey):
            return None
        return self.count[countKey]

    def incrementCount(self, dp):
        countKey = self.countKey(dp)
        if not self.count.has_key(countKey):
            self.resetCount(dp)
        self.count[countKey] += 1
        return self.count[countKey]

    def resetCount(self, dp):
        self.count[self.countKey(dp)] = 0

    def check(self, dataPoints):
        """The given datapoints have been updated, so re-evaluate.
        returns events or an empty sequence"""
        unused(dataPoints)
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
        unused(timeOf)
        result = []
        if value is None: return result
        try:
            cycleTime, rrdType = self.rrdInfoCache(dataPoint)
        except Exception:
            log.error('Unable to read RRD file for %s' % dataPoint)
            return result
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
        if type(value) in types.StringTypes:
            value = float(value)
        thresh = None
        if self.maximum is not None and value > self.maximum:
            thresh = self.maximum
            how = 'exceeded the maximum'
        if self.minimum is not None and value < self.minimum:
            thresh = self.minimum
            how = 'not met the minimum'
        if thresh is not None:
            severity = self.severity
            count = self.incrementCount(dp)
            if self.escalateCount and count >= self.escalateCount:
                severity = min(severity + 1, 5)
            summary = 'Threshold of %s %s: current value %.2f' % (
                self.name(), how, float(value))
            return [dict(device=self.context().deviceName,
                         summary=summary,
                         eventKey=self.id,
                         eventClass=self.eventClass,
                         component=self.context().componentName,
                         severity=severity)]
        else:
            count = self.getCount(dp)
            if count is None or count > 0:
                summary = 'Threshold of %s restored: current value: %.2f' % (
                    self.name(), value)
                self.resetCount(dp)
                return [dict(device=self.context().deviceName,
                             summary=summary,
                             eventKey=self.id,
                             eventClass=self.eventClass,
                             component=self.context().componentName,
                             severity=Event.Clear)]
        return []


    def getGraphElements(self, template, context, gopts, namespace, color, 
                         legend, relatedGps):
        """Produce a visual indication on the graph of where the
        threshold applies."""
        unused(template, namespace)
        if not color.startswith('#'):
            color = '#%s' % color
        n = self.minimum
        x = self.maximum
        if not self.dataPointNames:
            return gopts
        gp = relatedGps[self.dataPointNames[0]]
        rpn = getattr(gp, 'rpn', None)
        if rpn:
            rpn = talesEvalStr(rpn, context)
            n = rpneval(n, rpn)
            x = rpneval(x, rpn)
        result = []
        if n:
            result += [
                "HRULE:%s%s:%s\\j" % (n, color, 
                          legend or self.getMinLabel(n, relatedGps)),
                ]
        if x:
            result += [
                "HRULE:%s%s:%s\\j" % (x, color, 
                          legend or self.getMaxLabel(x, relatedGps)) 
                ]
        return gopts + result


    def getMinLabel(self, minval, relatedGps):
        """build a label for a min threshold"""
        return "%s < %s" % (self.getNames(relatedGps), self.setPower(minval)) 


    def getMaxLabel(self, maxval, relatedGps):
        """build a label for a max threshold"""
        return "%s > %s" % (self.getNames(relatedGps), self.setPower(maxval))

    def getNames(self, relatedGps):
        legends = [ getattr(gp, 'legend', gp) for gp in relatedGps.values() ] 
        return ', '.join(legends) 

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
