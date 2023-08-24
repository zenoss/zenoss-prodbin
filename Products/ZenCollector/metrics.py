import re
import time

from twisted.internet import defer

from Products.ZenUtils import metrics


class CollectorMetrics(object):
    """
    """

    def __init__(self, traceMetricName=None, traceMetricKey=None):
        """
        """
        self._traceMetricName = traceMetricName
        self._traceMetricKey = traceMetricKey
        self._derivative_tracker = None
        self._metric_writer = None
        self._threshold_notifier = None

    def should_trace_metric(self, metric, contextkey):
        """
        Tracer implementation - use this function to indicate whether a given
        metric/contextkey combination is to be traced.

        :param metric: name of the metric in question
        :type metric: str
        :param contextkey: context key of the metric in question
        :return: boolean indicating whether to trace this metric/key
        """
        tests = []
        if self._traceMetricName:
            tests.append((self._traceMetricName, metric))
        if self._traceMetricKey:
            tests.append((self._traceMetricKey, contextkey))
        result = [bool(re.search(exp, subj)) for exp, subj in tests]
        return len(result) > 0 and all(result)

    @defer.inlineCallbacks
    def writeMetric(
        self,
        contextKey,
        metric,
        value,
        metricType,
        contextId,
        timestamp="N",
        min="U",
        max="U",
        threshEventData=None,
        deviceId=None,
        contextUUID=None,
        deviceUUID=None,
        extraTags=None,
    ):
        """
        Writes the metric to the metric publisher.

        :param contextKey: This is who the metric applies to. This is usually
            the return value of rrdPath() for a component or device.
        :param metric: the name of the metric, we expect it to be of the form
            datasource_datapoint.
        :param value: the value of the metric.
        :param metricType: type of the metric (e.g. 'COUNTER', 'GAUGE',
            'DERIVE' etc)
        :param contextId: used for the threshold events, the id of who this
            metric is for.
        :param timestamp: defaults to time.time() if not specified,
            the time the metric occurred.
        :param min: used in the derive the min value for the metric.
        :param max: used in the derive the max value for the metric.
        :param threshEventData: extra data put into threshold events.
        :param deviceId: the id of the device for this metric.
        :return: a deferred that fires when the metric gets published.
        """
        timestamp = int(time.time()) if timestamp == "N" else timestamp
        tags = {"contextUUID": contextUUID, "key": contextKey}
        if self.should_trace_metric(metric, contextKey):
            tags["mtrace"] = "{}".format(int(time.time()))

        metric_name = metric
        if deviceId:
            tags["device"] = deviceId

        # compute (and cache) a rate for COUNTER/DERIVE
        if metricType in {"COUNTER", "DERIVE"}:
            if metricType == "COUNTER" and min == "U":
                # COUNTER implies only positive derivatives are valid.
                min = 0

            dkey = "%s:%s" % (contextUUID, metric)
            value = self._derivative_tracker.derivative(
                dkey, (float(value), timestamp), min, max
            )

        # check for threshold breaches and send events when needed
        if value is not None:
            if extraTags:
                tags.update(extraTags)

            # write the  metric to Redis
            try:
                yield defer.maybeDeferred(
                    self._metric_writer.write_metric,
                    metric_name,
                    value,
                    timestamp,
                    tags,
                )
            except Exception as e:
                self.log.debug("Error sending metric %s", e)
            yield defer.maybeDeferred(
                self._threshold_notifier.notify,
                contextUUID,
                contextId,
                metric,
                timestamp,
                value,
                threshEventData,
            )

    def writeMetricWithMetadata(
        self,
        metric,
        value,
        metricType,
        timestamp="N",
        min="U",
        max="U",
        threshEventData=None,
        metadata=None,
        extraTags=None,
    ):
        metadata = metadata or {}
        try:
            key = metadata["contextKey"]
            contextId = metadata["contextId"]
            deviceId = metadata["deviceId"]
            contextUUID = metadata["contextUUID"]
            if metadata:
                metric_name = metrics.ensure_prefix(metadata, metric)
            else:
                metric_name = metric
        except KeyError as e:
            raise Exception("Missing necessary metadata: %s" % e.message)

        return self.writeMetric(
            key,
            metric_name,
            value,
            metricType,
            contextId,
            timestamp=timestamp,
            min=min,
            max=max,
            threshEventData=threshEventData,
            deviceId=deviceId,
            contextUUID=contextUUID,
            deviceUUID=metadata.get("deviceUUID"),
            extraTags=extraTags,
        )
