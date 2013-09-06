##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import logging
from Products.ZenRRD.Thresholds import Thresholds

log = logging.getLogger("zen.MetricWriter")


class MetricWriter(object):

    def __init__(self, publisher):
        self._publisher = publisher
        self._datapoints = 0

    def write_metric(self, metric, value, timestamp, tags):
        """
        Wraps calls to a deferred publisher

        @param metric:
        @param value:
        @param timestamp:
        @param tags:
        @return:
        """
        try:
            log.debug("publishing metric %s %s %s %s", metric, value, timestamp, tags)
            self._publisher.put(metric, value, timestamp, tags)
            self._datapoints += 1
        except Exception as x:
            log.exception(x)

    @property
    def dataPoints(self):
        """
        The number of datapoints that have been published
        @return: int
        """
        return self._datapoints


class DerivativeTracker(object):

    def __init__(self):
        self._timed_metric_cache = {}

    def derivative(self, name, timed_metric, min='U', max='U'):
        """
        Tracks a metric value over time and returns deltas

        @param name: used to track a specific metric over time
        @param timed_metric: tuple of (value, timestamp)
        @param min: restricts minimum value returned
        @param max: restricts maximum value returned
        @return: change from previous value if a previous value exists
        """
        last_timed_metric = self._timed_metric_cache.get(name)
        if last_timed_metric:
            # identical timestamps?
            if timed_metric[1] == last_timed_metric[1]:
                return 0
            else:
                delta = float(timed_metric[0] - last_timed_metric[0]) / \
                    float(timed_metric[1] - last_timed_metric[1])
                if isinstance(min, (int, float)) and delta < min:
                    delta = min
                if isinstance(max, (int, float)) and delta > max:
                    delta = max
                return delta
        else:
            # first value we've seen for path
            self._timed_metric_cache[name] = timed_metric
            return None


class ThresholdNotifier(object):
    """
    Encapsulates the logic necessary to evaluate a datapoint value
    against thresholds and send any events that are generated from
    threshold evaluation. Used by CollectorDaemon and DaemonStats.
    """
    def __init__(self, send_callback, thresholds):
        self._send_callback = send_callback
        if isinstance(thresholds, list):
            self._thresholds = Thresholds()
            self._thresholds.updateList(thresholds)
        elif isinstance(thresholds, Thresholds):
            self._thresholds = thresholds
        else:
            self._thresholds = Thresholds()

    def updateThresholds(self, thresholds):
        self._thresholds.updateList(thresholds)


    def notify(self, context_uuid, context_id, metric, timestamp, value, thresh_event_data={}):
        """
        Check the specified value against thresholds and send any generated
        events

        @param context_uuid: context name used to check thresholds
        @param context_id: can be used for event key prefix
        @param metric: name of the metric
        @param timestamp: timestamp for the value
        @param value: the value to check
        @param thresh_event_data: additional data to send with any events
        @return:
        """
        if self._thresholds and value is not None:
            if 'eventKey' in thresh_event_data:
                eventKeyPrefix = [thresh_event_data['eventKey']]
            else:
                eventKeyPrefix = [context_id]
            for ev in self._thresholds.check(context_uuid, metric, timestamp, value):
                parts = eventKeyPrefix[:]
                if 'eventKey' in ev:
                    parts.append(ev['eventKey'])
                ev['eventKey'] = '|'.join(parts)
                # add any additional values for this threshold
                # (only update if key is not in event, or if
                # the event's value is blank or None)
                for key, value in thresh_event_data.items():
                    if ev.get(key, None) in ('', None):
                        ev[key] = value
                self._send_callback(ev)
