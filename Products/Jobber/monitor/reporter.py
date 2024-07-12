##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import contextlib
import json
import logging

import attr
import requests

from attr.validators import instance_of, deep_mapping

from Products.ZenUtils.controlplane import configuration as cc_config
from Products.ZenUtils.MetricReporter import DEFAULT_METRIC_URL


class MetricsReporter(object):
    def __init__(self, url=None, prefix=""):
        if not url:
            url = cc_config.consumer_url
            if not url:
                url = DEFAULT_METRIC_URL
        self._url = url
        self._log = logging.getLogger("zen.zenjobs.monitor.reporter")

    @contextlib.contextmanager
    def session(self, tags=None):
        session = _Session(tags if tags is not None else {})
        try:
            yield session
        except Exception:
            self._log.exception("metrics reporting session failed")
        else:
            self._post(session.metrics)

    def _post(self, metrics):
        if not metrics:
            return
        session = requests.Session()
        session.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "Zenoss Service Metrics",
            }
        )
        body = {"metrics": [attr.asdict(sample) for sample in metrics]}
        self._log.debug("sending metric payload: {}", body)
        response = session.post(self._url, data=json.dumps(body))
        if response.status_code != 200:
            self._log.warning(
                "problem submitting metrics: {}, {}",
                response.status_code,
                response.text.replace("\n", "\\n"),
            )
        else:
            self._log.debug("{} metrics posted", len(metrics))

    def build_metric(self, **kw):
        metric = Metric(**kw)
        metric.tags.update(
            {
                "tenantId": cc_config.tenant_id,
                "serviceId": metric.tags["controlplane_service_id"],
            }
        )
        return metric


class _Session(object):
    def __init__(self, tags):
        self._tags = tags
        self.metrics = []

    def add(self, metric, value, timestamp, tags=None):
        tags = tags if tags is not None else {}
        tags.update(self._tags)
        self.metrics.append(
            Metric(metric=metric, value=value, timestamp=timestamp, tags=tags)
        )


@attr.s(frozen=True, slots=True)
class Metric(object):
    metric = attr.ib(converter=str)
    value = attr.ib(converter=float)
    timestamp = attr.ib(validator=instance_of(float))
    tags = attr.ib(
        validator=deep_mapping(
            key_validator=instance_of(str),
            value_validator=instance_of(str),
            mapping_validator=instance_of(dict),
        )
    )

    @tags.validator
    def _verify_keys(self, attribute, value):
        if "controlplane_service_id" not in value:
            raise KeyError("Missing 'controlplane_service_id' tag")