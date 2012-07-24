##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenModel.ThresholdInstance import RRDThresholdInstance

__doc__= """Threshold to track when a value changes.
"""

from Globals import InitializeClass
from ThresholdClass import ThresholdClass
from ThresholdInstance import ThresholdContext
from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_INFO
from Products.ZenEvents.ZenEventClasses import Status_Perf

import logging
log = logging.getLogger('zen.MinMaxCheck')


NaN = float('nan')

class ValueChangeThreshold(ThresholdClass):
    """
    Threshold that can watch changes in a value
    """
    
    eventClass = Status_Perf
    severity = SEVERITY_INFO

    def createThresholdInstance(self, context):
        """Return the config used by the collector to process change thresholds
        """
        mmt = ValueChangeThresholdInstance(self.id,
                                      ThresholdContext(context),
                                      self.dsnames,
                                      eventClass=self.eventClass,
                                      severity=self.severity)
        return mmt

InitializeClass(ValueChangeThreshold)
ValueChangeThresholdClass = ValueChangeThreshold

class ValueChangeThresholdInstance(RRDThresholdInstance):
    """
    Threshold that emits an event when a value changes from its previous value. Does not send clear events.
    """

    def __init__(self, id, context, dpNames, eventClass, severity):
        RRDThresholdInstance.__init__(self, id, context, dpNames, eventClass, severity)
        self._lastValues = {}

    def _checkImpl(self, dataPoint, value):
        dpKey = self._getDpKey(dataPoint)
        lastValue = self._lastValues.get(dpKey, None)
        if lastValue != value:
            self._lastValues[dpKey] = value
            event = dict(
                device=self.context().deviceName,
                summary="Value changed from %s to %s" % (lastValue, value),
                eventKey=self.id,
                eventClass=self.eventClass,
                component=self.context().componentName,
                current=value,
                previous=lastValue,
                severity=self.severity)
            return (event,)
        return tuple()

    def _getDpKey(self, dp):
        return ':'.join(self.context().key()) + ':' + dp


from twisted.spread import pb
pb.setUnjellyableForClass(ValueChangeThresholdInstance, ValueChangeThresholdInstance)
