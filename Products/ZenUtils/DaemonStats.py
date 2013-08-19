##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals


class DaemonStats(object):
    """
    Utility for a daemon to write out internal performance statistics
    """

    def __init__(self):
        self.name = ""
        self.monitor = ""
        self.metric_writer = None

    def config(self, name, monitor, metric_writer):
        """
        Initialize the object.  We could do this in __init__, but
        that would delay creation to after configuration time, which
        may run asynchronously with collection or heartbeats.  By
        deferring initialization, this object implements the Null
        Object pattern until the application is ready to start writing
        real statistics.
        """
        self.name = name
        self.monitor = monitor
        self.metric_writer = metric_writer

    def _uuid(self):
        return self.name + "-" + self.monitor

    def _metric(self, name):
        return self.monitor + "_" + name

    def _context_id(self):
        return self.monitor

    def derive(self, name, cycleTime, value):
        """Write a DERIVE value, return empty list"""
        self.metric_writer.writeMetric(
            self._uuid(), self._metric(name), value, 'DERIVE',
            self._context_id(), hasThresholds=True)
        return []

    def counter(self, name, cycleTime, value):
        """Write a DERIVE value, return empty list"""
        self.metric_writer.writeMetric(
            self._uuid(), self._metric(name), value, 'COUNTER',
            self._context_id(), hasThresholds=True)
        return []

    def gauge(self, name, cycleTime, value):
        self.metric_writer.writeMetric(
            self._uuid(), self._metric(name), value, 'GAUGE',
            self._context_id(), hasThresholds=True)
        return []
