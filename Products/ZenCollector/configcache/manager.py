##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import gc
import logging

from datetime import datetime
from time import time

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from .app import Application
from .app.args import get_subparser
from .cache import ConfigStatus
from .constants import Constants
from .debug import Debug as DebugCommand
from .propertymap import DevicePropertyMap
from .task import BuildConfigTaskDispatcher
from .utils import getConfigServices

_default_interval = 30.0  # seconds


class Manager(object):

    description = (
        "Determines whether device configs are old and regenerates them"
    )

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(subparsers, "manager", Manager.description)
        subsubparsers = subp.add_subparsers(title="Manager Commands")

        subp_run = get_subparser(
            subsubparsers, "run", "Run the manager service"
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
            "Signal the manager service to toggle debug logging",
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

    def run(self):
        self.log.info(
            "checking for expired configurations and configuration build "
            "timeouts every %s seconds",
            self.interval,
        )
        while not self.ctx.controller.shutdown:
            try:
                self.ctx.session.sync()
                gc.collect()
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
                "%s=%s %s=%s service=%s monitor=%s device=%s",
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

        # Retrieve the 'retired' configs
        ready_to_rebuild = list(
            status
            for status in self.store.get_retired()
            if status.updated < now - minttl_map.get(status.uid)
        )

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
            self.store.set_pending((status.key, time()))
            self.dispatcher.dispatch(
                status.key.service,
                status.key.monitor,
                status.key.device,
                timeout,
            )
            if isinstance(status, ConfigStatus.Expired):
                self.log.info(
                    "submitted job to rebuild expired config  "
                    "service=%s monitor=%s device=%s",
                    status.key.service,
                    status.key.monitor,
                    status.key.device,
                )
            elif isinstance(status, ConfigStatus.Retired):
                self.log.info(
                    "submitted job to rebuild retired config  "
                    "service=%s monitor=%s device=%s",
                    status.key.service,
                    status.key.monitor,
                    status.key.device,
                )
            else:
                self.log.info(
                    "submitted job to rebuild old config  "
                    "updated=%s %s=%s service=%s monitor=%s device=%s",
                    datetime.fromtimestamp(status.updated).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    Constants.time_to_live_id,
                    timeout,
                    status.key.service,
                    status.key.monitor,
                    status.key.device,
                )
            count += 1
        if count == 0:
            self.log.debug("found no expired or old configurations to rebuild")
