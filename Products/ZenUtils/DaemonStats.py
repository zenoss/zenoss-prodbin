##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Globals
import time


class DaemonStats(object):
    """
    Utility for a daemon to write out internal perfo
    rmance statistics
    """

    def __init__(self):
        self.name = ""
        self.monitor = ""
        self.metric_writer = None

    def config(self, name, monitor, metric_writer, threshold_notifier,
               derivative_tracker):
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
        self._metric_writer = metric_writer
        self._threshold_notifier = threshold_notifier
        self._derivative_tracker = derivative_tracker

    def _context_id(self):
        return self.name + "-" + self.monitor

    def _tags(self):
        return {
            'daemon': self.name,
            'monitor': self.monitor
        }

    def derive(self, name, cycleTime, value):
        """Write a DERIVE value, return empty list"""
        tags = self._tags()
        tags['metricType'] = 'DERIVE'
        self._post_metrics(name, value, tags)
        return []

    def counter(self, name, cycleTime, value):
        """Write a DERIVE value, return empty list"""
        tags = self._tags()
        tags['metricType'] = 'COUNTER'
        self._post_metrics(name, value, tags)
        return []

    def gauge(self, name, cycleTime, value):
        """Write a DERIVE value, return empty list"""
        tags = self._tags()
        tags['metricType'] = 'GAUGE'
        self._post_metrics(name, value, tags)
        return []

    def _post_metrics(self, name, value, tags):
        timestamp = time.time()
        self._metric_writer.write_metric(name, value, timestamp, tags)

        context_id = self._context_id()

        if tags['metricType'] in {'DERIVE', 'COUNTER'}:
            # compute (and cache) a rate for COUNTER/DERIVE
            value = self._derivative_tracker.derivative(
                context_id, (int(value), timestamp))

            # check for threshold breaches and send events when needed
            self._threshold_notifier.notify(
                context_id, context_id, timestamp, value)

