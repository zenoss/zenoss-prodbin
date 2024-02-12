##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import logging

from collections import Counter, defaultdict
from datetime import datetime
from time import time

import attr

from metrology.instruments import Gauge, HistogramExponentiallyDecaying
from metrology.utils.periodic import PeriodicTask
from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from .app import Application
from .app.args import get_subparser
from .cache import ConfigStatus
from .constants import Constants
from .debug import Debug as DebugCommand
from .dispatcher import BuildConfigTaskDispatcher
from .propertymap import DevicePropertyMap
from .utils import getConfigServices

_default_interval = 30.0  # seconds


class Manager(object):

    description = (
        "Determines whether device configs are old and regenerates them"
    )

    metric_prefix = "configcache.status."

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers, "manager", description=Manager.description
        )
        subsubparsers = subp.add_subparsers(title="Manager Commands")

        subp_run = get_subparser(
            subsubparsers, "run", description="Run the manager service"
        )
        Application.add_all_arguments(subp_run)
        subp_run.add_argument(
            "--check-interval",
            default=_default_interval,
            type=float,
            help="Config checking interval (in seconds)",
        )
        subp_run.set_defaults(
            factory=Application.from_args,
            parser=subp_run,
            task=Manager,
        )

        subp_debug = get_subparser(
            subsubparsers,
            "debug",
            description="Signal the manager service to toggle debug logging",
        )
        Application.add_pidfile_arguments(subp_debug)
        subp_debug.set_defaults(factory=DebugCommand.from_args)

        Application.add_genconf_command(subsubparsers, (subp_run, subp_debug))

    def __init__(self, config, context):
        self.ctx = context
        configClasses = getConfigServices()
        self.dispatcher = BuildConfigTaskDispatcher(configClasses)
        client = getRedisClient(url=getRedisUrl())
        self.store = createObject("configcache-store", client)
        self.interval = config["check-interval"]
        self.log = logging.getLogger("zen.configcache.manager")

        # metrics
        self.ctx.metric_reporter.add_tags({"zenoss_daemon": "manager"})
        self._metric_collector = _MetricCollector(self.ctx.metric_reporter)

    def run(self):
        self.log.info(
            "checking for expired configurations and configuration build "
            "timeouts every %s seconds",
            self.interval,
        )
        try:
            self._metric_collector.start()
            self._main()
        finally:
            self._metric_collector.stop()
            self._metric_collector.join(timeout=5)

    def _main(self):
        while not self.ctx.controller.shutdown:
            try:
                self.ctx.session.sync()
                timedout = tuple(self._get_build_timeouts())
                if not timedout:
                    self.log.debug("no configuration builds have timed out")
                else:
                    self._expire_configs(timedout, "build")
                timedout = tuple(self._get_pending_timeouts())
                if not timedout:
                    self.log.debug(
                        "no pending configuration builds have timed out"
                    )
                else:
                    self._expire_configs(timedout, "pending")
                statuses = self._get_configs_to_rebuild()
                if statuses:
                    self._rebuild_configs(statuses)
            except Exception as ex:
                self.log.exception("unexpected error %s", ex)
            finally:
                # Call cacheGC to aggressively trim the ZODB cache
                self.ctx.session.cacheGC()
            self.ctx.controller.wait(self.interval)

    def _get_build_timeouts(self):
        buildlimitmap = DevicePropertyMap.make_build_timeout_map(
            self.ctx.dmd.Devices
        )
        # Test against a time 10 minutes earlier to minimize interfering
        # with builder working on the same config.
        now = time() - 600
        for status in self.store.get_building():
            limit = buildlimitmap.get(status.uid)
            if status.started < (now - limit):
                yield (
                    status,
                    "started",
                    status.started,
                    Constants.build_timeout_id,
                    limit,
                )

    def _get_pending_timeouts(self):
        pendinglimitmap = DevicePropertyMap.make_pending_timeout_map(
            self.ctx.dmd.Devices
        )
        now = time()
        for status in self.store.get_pending():
            limit = pendinglimitmap.get(status.uid)
            if status.submitted < (now - limit):
                yield (
                    status,
                    "submitted",
                    status.submitted,
                    Constants.pending_timeout_id,
                    limit,
                )

    def _expire_configs(self, data, kind):
        now = time()
        self.store.set_expired(
            *((status.key, now) for status, _, _, _, _ in data)
        )
        for status, valId, val, limitId, limitValue in data:
            self.log.info(
                "expired configuration due to %s timeout  "
                "%s=%s %s=%s service=%s collector=%s device=%s",
                kind,
                valId,
                datetime.fromtimestamp(val).strftime("%Y-%m-%d %H:%M:%S"),
                limitId,
                limitValue,
                status.key.service,
                status.key.monitor,
                status.key.device,
            )

    def _get_configs_to_rebuild(self):
        minttl_map = DevicePropertyMap.make_minimum_ttl_map(
            self.ctx.dmd.Devices
        )
        ttl_map = DevicePropertyMap.make_ttl_map(self.ctx.dmd.Devices)
        now = time()

        ready_to_rebuild = []

        # Retrieve the 'retired' configs
        for status in self.store.get_retired():
            built = self.store.get_updated(status.key)
            if built is None or built < now - minttl_map.get(status.uid):
                ready_to_rebuild.append(status)

        # Append the 'expired' configs
        ready_to_rebuild.extend(self.store.get_expired())

        # Append the 'older' configs.
        min_age = now - ttl_map.smallest_value()
        for status in self.store.get_older(min_age):
            # Select the min ttl if the ttl is a smaller value
            limit = max(minttl_map.get(status.uid), ttl_map.get(status.uid))
            expiration_threshold = now - limit
            if status.updated <= expiration_threshold:
                ready_to_rebuild.append(status)

        return ready_to_rebuild

    def _rebuild_configs(self, statuses):
        buildlimitmap = DevicePropertyMap.make_build_timeout_map(
            self.ctx.dmd.Devices
        )
        count = 0
        for status in statuses:
            timeout = buildlimitmap.get(status.uid)
            now = time()
            self.store.set_pending((status.key, now))
            self.dispatcher.dispatch(
                status.key.service,
                status.key.monitor,
                status.key.device,
                timeout,
                now,
            )
            if isinstance(status, ConfigStatus.Expired):
                self.log.info(
                    "submitted job to rebuild expired config  "
                    "service=%s collector=%s device=%s",
                    status.key.service,
                    status.key.monitor,
                    status.key.device,
                )
            elif isinstance(status, ConfigStatus.Retired):
                self.log.info(
                    "submitted job to rebuild retired config  "
                    "service=%s collector=%s device=%s",
                    status.key.service,
                    status.key.monitor,
                    status.key.device,
                )
            else:
                self.log.info(
                    "submitted job to rebuild old config  "
                    "updated=%s %s=%s service=%s collector=%s device=%s",
                    datetime.fromtimestamp(status.updated).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    Constants.build_timeout_id,
                    timeout,
                    status.key.service,
                    status.key.monitor,
                    status.key.device,
                )
            count += 1
        if count == 0:
            self.log.debug("found no expired or old configurations to rebuild")


class _MetricCollector(PeriodicTask):

    def __init__(self, reporter):
        super(_MetricCollector, self).__init__(interval=60)
        self._reporter = reporter
        self._metrics = _Metrics(reporter)
        self._store = None

    def task(self):
        if self._store is None:
            client = getRedisClient(url=getRedisUrl())
            self._store = createObject("configcache-store", client)
        self._collect()
        self._reporter.save()

    def _collect(self):
        counts = Counter()
        ages = defaultdict(list)
        now = time()
        for status in self._store.query_statuses():
            key, uid, ts = attr.astuple(status)
            ages[type(status)].append(int(now - ts))
            counts.update([type(status)])

        self._metrics.count.current.mark(counts.get(ConfigStatus.Current, 0))
        self._metrics.count.retired.mark(counts.get(ConfigStatus.Retired, 0))
        self._metrics.count.expired.mark(counts.get(ConfigStatus.Expired, 0))
        self._metrics.count.pending.mark(counts.get(ConfigStatus.Pending, 0))
        self._metrics.count.building.mark(counts.get(ConfigStatus.Building, 0))

        for age in ages.get(ConfigStatus.Current, []):       
            self._metrics.age.current.update(age)
        for age in ages.get(ConfigStatus.Expired, []):       
            self._metrics.age.retired.update(age)
        for age in ages.get(ConfigStatus.Retired, []):       
            self._metrics.age.expired.update(age)
        for age in ages.get(ConfigStatus.Pending, []):       
            self._metrics.age.pending.update(age)
        for age in ages.get(ConfigStatus.Building, []):       
            self._metrics.age.building.update(age)


class StatusCountGauge(Gauge):

    def __init__(self):
        self._value = 0

    @property
    def value(self):
        return self._value

    def mark(self, value):
        self._value = value


class _Metrics(object):

    def __init__(self, reporter):
        self.count = type(
            "Count",
            (object,),
            {
                "current": StatusCountGauge(),
                "retired": StatusCountGauge(),
                "expired": StatusCountGauge(),
                "pending": StatusCountGauge(),
                "building": StatusCountGauge(),
            },
        )()
        reporter.register("count.current", self.count.current)
        reporter.register("count.retired", self.count.retired)
        reporter.register("count.expired", self.count.expired)
        reporter.register("count.pending", self.count.pending)
        reporter.register("count.building", self.count.building)
        self.age = type(
            "Age",
            (object,),
            {
                "current": HistogramExponentiallyDecaying(),
                "retired": HistogramExponentiallyDecaying(),
                "expired": HistogramExponentiallyDecaying(),
                "pending": HistogramExponentiallyDecaying(),
                "building": HistogramExponentiallyDecaying(),
            },
        )()
        reporter.register("age.current", self.age.current)
        reporter.register("age.retired", self.age.retired)
        reporter.register("age.expired", self.age.expired)
        reporter.register("age.pending", self.age.pending)
        reporter.register("age.building", self.age.building)
