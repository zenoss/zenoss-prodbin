##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os

import Globals
import rrdtool
from Products.ZenModel.PerformanceConf import PerformanceConf, performancePath
from Products.ZenModel.MonitorClass import MonitorClass
from Products.ZenUtils.Utils import unused, rrd_daemon_args, rrd_daemon_retry

from twisted.spread import pb

import logging
log = logging.getLogger('zen.ThresholdInstance')

unused(Globals)

class ThresholdContext(pb.Copyable, pb.RemoteCopy):
    """Remember all the little details about a specific data point
    within a context.  This is useful for error messages and path
    information in the collectors.  It's a copy of the key bits of
    information from the Model."""
    
    def __init__(self, context):
        if isinstance(context, MonitorClass):
            self.deviceName = "{context.id} hub".format(context=context)
            self.componentName = ''
            self.deviceUrl = 'zport/dmd/Monitors/Hub/{context.id}/viewHubPerformance'.format(context=context)
            self.devicePath = 'Monitors/Hub/{context.id}'.format(context=context)
        elif isinstance(context, PerformanceConf):
            self.deviceName = "{context.id} collector".format(context=context)
            self.componentName = ''
            self.deviceUrl = 'zport/dmd/Monitors/Performance/{context.id}/viewDaemonPerformance'.format(context=context)
            self.devicePath = 'Monitors/Performance/{context.id}'.format(context=context)
        else:
            self.deviceName = context.device().id
            self.componentName = context.id
            if self.componentName == self.deviceName:
                self.componentName = ''

        self.rrdPath = context.rrdPath()


    def key(self):
        "Unique data that refers this context"
        return self.deviceName, self.componentName


    def fileKey(self, dataPoint):
        "Unique base filename for this context and given dataPoint"
        return os.path.join(self.rrdPath, dataPoint)

    
    def path(self, dataPoint):
        "The full pathname to RRD file that uses a dataPoint"
        return performancePath(os.path.join(self.rrdPath, dataPoint)) + '.rrd'

pb.setUnjellyableForClass(ThresholdContext, ThresholdContext)

class ThresholdInstance(pb.Copyable, pb.RemoteCopy):
    """A ThresholdInstance is a threshold to be evaluated in a
    collector within a given context."""

    # count is unknown if None
    count = None
        
    def name(self):
        "return the name of this threshold (from the ThresholdClass)"

    def context(self):
        "Return the ThresholdContext for this ThresholdInstance"

    def key(self):
        "Unique data that refers to this object within a collector"
        return self.name(), self.context().key()

    def dataPoints(self):
        "Returns the names of the datapoints used to compute the threshold"

    def check(self, dataPoints):
        """The given datapoints have been updated, so re-evaluate.
        returns events or an empty sequence"""

    def checkRaw(self, dataPoint, timeOf, value):
        """A new datapoint has been collected, use the given _raw_
        value to re-evalue the threshold.
        returns a sequence of events.
        """
        unused(timeOf, value)
        return self.check([dataPoint])

    def getGraphElements(self, template, context, gopts, namespace, color,
                         legend, relatedGps):
        """Produce a visual indication on the graph of where the
        threshold applies."""
        unused(template, context, gopts, namespace, color, legend, relatedGps)
        return []


pb.setUnjellyableForClass(ThresholdInstance, ThresholdInstance)

class RRDThresholdInstance(ThresholdInstance):

    def __init__(self, id, context, dpNames, eventClass, severity):
        self._context = context
        self.id = id
        self.eventClass = eventClass
        self.severity = severity
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

    def check(self, dataPoints):
        """The given datapoints have been updated, so re-evaluate.
        returns events or an empty sequence"""
        unused(dataPoints)
        result = []
        for dp in self.dataPointNames:
            cycleTime, rrdType = self._getRRDType(dp)
            result.extend(self._checkImpl(
                dp, self._fetchLastValue(dp, cycleTime)))
        return result

    def checkRaw(self, dataPoint, timeOf, value):
        """A new datapoint has been collected, use the given _raw_
        value to re-evalue the threshold."""
        unused(timeOf)
        result = []
        if value is None: return result
        try:
            cycleTime, rrdType = self._getRRDType(dataPoint)
        except Exception:
            log.exception('Unable to read RRD file for %s' % dataPoint)
            return result
        if rrdType != 'GAUGE' and value is None:
            value = self._fetchLastValue(dataPoint, cycleTime)
        result.extend(self._checkImpl(dataPoint, value))
        return result

    def _getRRDType(self, dp):
        """
        get and cache rrd type inforomation
        """
        if dp in self._rrdInfoCache:
            return self._rrdInfoCache[dp]

        @rrd_daemon_retry
        def rrdtool_fn():
            return rrdtool.info(self.context().path(dp), *rrd_daemon_args())
        data = rrdtool_fn()
                
        # handle both old and new style RRD versions
        try:
            # old style 1.2.x
            value = data['step'], data['ds']['ds0']['type']
        except KeyError:
            # new style 1.3.x
            value = data['step'], data['ds[ds0].type']
        self._rrdInfoCache[dp] = value
        return value


    def _fetchLastValue(self, dp, cycleTime):
        """
        Fetch the most recent value for a data point from the RRD file.
        """
        @rrd_daemon_retry
        def rrdtool_fn():
            return rrdtool.fetch(self.context().path(dp),
                'AVERAGE', '-s', 'now-%d' % (cycleTime*2), '-e', 'now',
                *rrd_daemon_args())
        startStop, names, values = rrdtool_fn()
        values = [ v[0] for v in values if v[0] is not None ]
        if values: return values[-1]


    def _checkImpl(self, dataPoint, value):
        raise NotImplementedError()

pb.setUnjellyableForClass(RRDThresholdInstance, RRDThresholdInstance)
