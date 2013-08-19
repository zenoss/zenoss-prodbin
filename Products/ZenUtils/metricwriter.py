##############################################################################
#
# Copyright (C) Zenoss, Inc. 2013, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
import time
import logging
from Products.ZenRRD.Thresholds import Thresholds
from twisted.internet import defer


log = logging.getLogger("zen.MetricWriter")


class MetricWriter(object):

    def __init__(self, sendEvent, publisher, thresholds):
        self._sendEvent = sendEvent
        self._publisher_def = publisher
        self._publisher = None
        if isinstance(thresholds, list):
            self._thresholds = Thresholds()
            self._thresholds.updateList(thresholds)
        elif isinstance(thresholds, Thresholds):
            self._thresholds = thresholds
        else:
            log.debug('thresholds was None or invalid type')
            self._thresholds = None
        self._metrics_channel = 'metrics'
        self._timedMetricCache = {}

    @defer.inlineCallbacks
    def _acquire_publisher(self):
        if not self._publisher:
            pub = yield self._publisher_def
            self._publisher = pub

    def _derivative(self, uuid, timedMetric, min, max):
        lastTimedMetric = self._timedMetricCache.get(uuid)
        if lastTimedMetric:
            # identical timestamps?
            if timedMetric[1] == lastTimedMetric[1]:
                return 0
            else:
                delta = float(timedMetric[0] - lastTimedMetric[0]) / float(timedMetric[1] - lastTimedMetric[1])
                if isinstance(min, (int, float)) and delta < min:
                    delta = min
                if isinstance(max, (int, float)) and delta > max:
                    delta = max
                return delta
        else:
            # first value we've seen for path
            self._timedMetricCache[uuid] = timedMetric
            return None

    def writeMetric(self, contextUUID, metric, value, metricType, contextId, timestamp='N', min='U', max='U',
                    hasThresholds=False, threshEventData={}, deviceuuid=None):
        """
        Writes the metric to the metric publisher.
        @param contextUUID: This is who the metric applies to. This is usually a component or a device.
        @param metric: the name of the metric, we expect it to be of the form datasource_datapoint
        @param value: the value of the metric
        @param metricType: type of the metric (e.g. 'COUNTER', 'GUAGE', 'DERIVE' etc)
        @param contextId: used for the threshold events, the id of who this metric is for
        @param timestamp: defaults to time.time() if not specified, the time the metric occurred
        @param min: used in the derive the min value for the metric
        @param max: used in the derive the max value for the metric
        @param hasThresholds: true if the metric has thresholds
        @param threshEventData: extra data put into threshold events
        @param deviceuuid: the unique identifier of the device for
        this metric, maybe the same as contextUUID if the context is a
        device
        """
        timestamp = int(time.time()) if timestamp == 'N' else timestamp
        extraTags = {
            'datasource': metric.split("_")[0]
        }
        if deviceuuid:
            extraTags['device'] = deviceuuid
            # write the raw metric to Redis

        self._acquire_publisher()
        self._publisher.put(self._metrics_channel,
                            metric.split("_")[1],  # metric id is the datapoint name
                            value,
                            timestamp,
                            contextUUID,
                            extraTags)

        # compute (and cache) a rate for COUNTER/DERIVE
        if metricType in ('COUNTER', 'DERIVE'):
            value = self._derivative(contextUUID, (int(value), timestamp), min, max)                   1

        # check for threshold breaches and send events when needed
        #import pdb
        #pdb.set_trace()
        if self._thresholds and value:
            if 'eventKey' in threshEventData:
                eventKeyPrefix = [threshEventData['eventKey']]
            else:
                eventKeyPrefix = [contextId]

            for ev in self._thresholds.check(contextUUID, timestamp, value):
                parts = eventKeyPrefix[:]
                if 'eventKey' in ev:
                    parts.append(ev['eventKey'])
                ev['eventKey'] = '|'.join(parts)

                # add any additional values for this threshold
                # (only update if key is not in event, or if
                # the event's value is blank or None)
                for key, value in threshEventData.items():
                    if ev.get(key, None) in ('', None):
                        ev[key] = value

                self._sendEvent(ev)
