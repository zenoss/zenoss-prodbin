import time

from contextlib import contextmanager

from zope.component import queryUtility

from Products.ZenHub.metricmanager import IMetricManager

METRIC_MANAGER = "invalidation_worker_metricmanager"
BUILD = "invalidation.config.build"


@contextmanager
def measureConfigBuild(service, deviceId):
    metrics = queryUtility(IMetricManager, METRIC_MANAGER)
    try:
        begin = time.time()
        yield
    finally:
        if not metrics:
            return
        end = time.time()
        metrics.metric_writer.write_metric(
            BUILD,
            toMillis(end - begin),  # duration
            toMillis(time.time()),  # timestamp
            {
                "monitor": service.instance,
                "service": service.name(),
                "device": deviceId,
            },
        )


def toMillis(seconds):
    return int(seconds * 1000)
