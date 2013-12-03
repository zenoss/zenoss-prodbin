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
    Utility for a daemon to write out internal performance statistics
    """

    def __init__(self):
        self.name = ""
        self.monitor = ""
        self.metric_writer = None
        self._threshold_notifier = None
        self._derivative_tracker = None

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

    def _contextKey(self):
        return "/".join(('Daemons', self.monitor))

    def _tags(self, metric_type):
        return {
            'daemon': self.name,
            'monitor': self.monitor,
            'metricType': metric_type
        }

    def derive(self, name, value):
        """Write a DERIVE value and post any relevant events"""
        self.post_metrics(name, value, 'DERIVE')

    def counter(self, name, value):
        """Write a COUNTER value and post any relevant events"""
        self.post_metrics(name, value, 'COUNTER')

    def gauge(self, name, value):
        """Write a GAUGE value and post any relevant events"""
        self.post_metrics(name, value, 'GAUGE')

    def post_metrics(self, name, value, metric_type):
        tags = self._tags(metric_type)
        timestamp = time.time()
        self._metric_writer.write_metric(name, value, timestamp, tags)

        context_id = self._context_id()

        if metric_type in {'DERIVE', 'COUNTER'}:
            # compute (and cache) a rate for COUNTER/DERIVE
            value = self._derivative_tracker.derivative(
                context_id, (int(value), timestamp))

        # check for threshold breaches and send events when needed
        self._threshold_notifier.notify(
            self._contextKey(), context_id, self.name+'_'+name, timestamp, value)

