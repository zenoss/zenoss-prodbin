import time

from contextlib import contextmanager

from zope.component import queryUtility

from Products.ZenHub.metricmanager import IMetricManager
from Products.ZenHub.server.service import ServiceReference

METRIC_MANAGER = "invalidation_worker_metricmanager"
BUILD = "invalidation.config.build"


@contextmanager
def measureConfigBuild(service, device):
    metrics = queryUtility(IMetricManager, METRIC_MANAGER)
    try:
        begin = time.time()
        yield
    finally:
        if not metrics:
            return
        end = time.time()
        path = device.deviceClass().getPrimaryPath()
        metrics.metric_writer.write_metric(
            BUILD,
            toMillis(end - begin),  # duration
            toMillis(time.time()),  # timestamp
            {
                "monitor": service.instance,
                "service": getServiceName(service),
                "device": device.name(),
                "deviceclass": "/".join(path[0:1] + path[4:]),
            },
        )


def getServiceName(service):
    if isinstance(service, ServiceReference):
        service = service.service
    return service.__class__.__name__


def toMillis(seconds):
    return int(seconds * 1000)
