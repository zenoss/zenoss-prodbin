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

from datetime import datetime
from itertools import chain
from time import time

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from .app import Application
from .cache import ConfigStatus
from .debug import Debug as DebugCommand
from .misc.args import get_subparser
from .utils import (
    BuildConfigTaskDispatcher,
    Constants,
    DevicePropertyMap,
    getConfigServices,
)

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
                self._retry_pending_builds()
                self._expire_retired_configs()
                self._rebuild_older_configs()
            except Exception as ex:
                self.log.exception("unexpected error %s", ex)
            self.ctx.controller.wait(self.interval)

    def _retry_pending_builds(self):
        pendinglimitmap = DevicePropertyMap.make_pending_timeout_map(
            self.ctx.dmd.Devices
        )
        now = time()
        count = 0
        for key, status in self.store.get_pending():
            uid = self.store.get_uid(key.device)
            duration = pendinglimitmap.get(uid)
            if status.submitted < (now - duration):
                self.store.set_expired(key)
                self.log.info(
                    "pending configuration build has timed out  "
                    "submitted=%s service=%s monitor=%s device=%s",
                    datetime.fromtimestamp(status.submitted).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    Constants.build_timeout_id,
                    duration,
                    key.service,
                    key.monitor,
                    key.device,
                )
                count += 1
        if count == 0:
            self.log.debug("no pending configuration builds have timed out")

    def _expire_retired_configs(self):
        retired = (
            (key, status, self.store.get_uid(key.device))
            for key, status in self.store.get_retired()
        )
        minttl_map = DevicePropertyMap.make_minimum_ttl_map(
            self.ctx.dmd.Devices
        )
        now = time()
        expire = tuple(
            key
            for key, status, uid in retired
            if status.updated < now - minttl_map.get(uid)
        )
        self.store.set_expired(*expire)

    def _rebuild_older_configs(self):
        buildlimitmap = DevicePropertyMap.make_build_timeout_map(
            self.ctx.dmd.Devices
        )
        ttlmap = DevicePropertyMap.make_ttl_map(self.ctx.dmd.Devices)
        min_ttl = ttlmap.smallest_value()
        self.log.debug(
            "minimum age limit is %s", _formatted_interval(min_ttl)
        )
        now = time()
        min_age = now - min_ttl
        results = chain.from_iterable(
            (self.store.get_expired(), self.store.get_older(min_age))
        )
        count = 0
        for key, status in results:
            uid = self.store.get_uid(key.device)
            ttl = ttlmap.get(uid)
            expiration_threshold = now - ttl
            if (
                isinstance(status, ConfigStatus.Expired)
                or status.updated <= expiration_threshold
            ):
                timeout = buildlimitmap.get(uid)
                self.store.set_pending((key, time()))
                self.dispatcher.dispatch(
                    key.service, key.monitor, key.device, timeout
                )
                if isinstance(status, ConfigStatus.Expired):
                    self.log.info(
                        "submitted job to rebuild expired config  "
                        "service=%s monitor=%s device=%s",
                        key.service,
                        key.monitor,
                        key.device,
                    )
                else:
                    self.log.info(
                        "submitted job to rebuild old config  "
                        "updated=%s %s=%s service=%s monitor=%s device=%s",
                        datetime.fromtimestamp(status.updated).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        Constants.time_to_live_id,
                        ttl,
                        key.service,
                        key.monitor,
                        key.device,
                    )
                count += 1
        if count == 0:
            self.log.debug("found no expired or old configurations to rebuild")


def _formatted_interval(total_seconds):
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    text = ""
    if seconds:
        text = "{:02} seconds".format(seconds)
    if minutes:
        text = "{:02} minutes {}".format(minutes, text).strip()
    if hours:
        text = "{:02} hours {}".format(hours, text).strip()
    if days:
        text = "{} days {}".format(days, text).strip()
    return text
