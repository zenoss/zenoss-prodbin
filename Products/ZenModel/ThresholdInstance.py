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

import os

import Globals
from Products.ZenModel.PerformanceConf import performancePath


from twisted.spread import pb
class ThresholdContext(pb.Copyable, pb.RemoteCopy):
    """Remember all the little details about a specific data point
    within a context.  This is useful for error messages and path
    information in the collectors.  It's a copy of the key bits of
    information from the Model."""
    
    def __init__(self, context):
        self.deviceName = context.device().id
        try:
            self.componentName = context.name()
        except AttributeError:
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
        return self.check([dataPoint])

    def getGraphElements(self, template, gopts, namespace, color):
        """Produce a visual indication on the graph of where the
        threshold applies."""
        return []


pb.setUnjellyableForClass(ThresholdInstance, ThresholdInstance)
