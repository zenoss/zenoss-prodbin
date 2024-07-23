##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import, division

import argparse
import sys

from zope.component import createObject

from Products.ZenUtils.init import initialize_environment
from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..app.args import get_subparser
from ..cache import CacheQuery

from .args import get_common_parser, MultiChoice
from ._tables import TablesOutput
from ._json import JSONOutput
from ._stats import (
    AverageAgeStat,
    CountStat,
    MaxAgeStat,
    MedianAgeStat,
    MinAgeStat,
    UniqueCountStat,
)
from ._groups import DeviceGroup, ServiceGroup, MonitorGroup, StatusGroup


class Stats(object):
    description = "Show statistics about the configuration cache"

    configs = (("stats.zcml", __name__),)

    _groups = ("collector", "device", "service", "status")
    _statistics = ("count", "avg_age", "median_age", "min_age", "max_age")

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers, "stats", Stats.description, parent=get_common_parser()
        )
        subp.add_argument(
            "-S",
            dest="statistic",
            action=MultiChoice,
            choices=Stats._statistics,
            default=argparse.SUPPRESS,
            help="Specify the statistics to return.  One or more statistics "
            "may be specified (comma separated). By default, all "
            "statistics are returned.",
        )
        subp.add_argument(
            "-G",
            dest="group",
            action=MultiChoice,
            choices=Stats._groups,
            default=argparse.SUPPRESS,
            help="Specify the statistics groupings to return.  One or more "
            "groupings may be specified (comma separated). By default, all "
            "groupings are returned.",
        )
        subp.add_argument(
            "-f",
            dest="format",
            choices=("tables", "json"),
            default="tables",
            help="Output statistics in the specified format",
        )
        subp.set_defaults(factory=Stats)

    def __init__(self, args):
        stats = []
        for statId in getattr(args, "statistic", Stats._statistics):
            if statId == "count":
                stats.append(CountStat)
            elif statId == "avg_age":
                stats.append(AverageAgeStat)
            elif statId == "median_age":
                stats.append(MedianAgeStat)
            elif statId == "min_age":
                stats.append(MinAgeStat)
            elif statId == "max_age":
                stats.append(MaxAgeStat)
        self._groups = []
        for groupId in getattr(args, "group", Stats._groups):
            if groupId == "collector":
                self._groups.append(MonitorGroup(stats))
            elif groupId == "device":
                try:
                    # DeviceGroup doesn't want CountStat
                    posn = stats.index(CountStat)
                except ValueError:
                    # Not found, so don't worry about it
                    dg_stats = stats
                    pass
                else:
                    # Found, replace it with UniqueCountStat
                    dg_stats = list(stats)
                    dg_stats[posn] = UniqueCountStat
                self._groups.append(DeviceGroup(dg_stats))
            if groupId == "service":
                self._groups.append(ServiceGroup(stats))
            elif groupId == "status":
                self._groups.append(StatusGroup(stats))
        if args.format == "tables":
            self._format = TablesOutput()
        elif args.format == "json":
            self._format = JSONOutput()
        self._monitor = "*{}*".format(args.collector).replace("***", "*")
        self._service = "*{}*".format(args.service).replace("***", "*")
        self._devices = getattr(args, "device", [])

    def run(self):
        haswildcard = any("*" in d for d in self._devices)
        if haswildcard and len(self._devices) > 1:
            print(
                "Only one DEVICE argument supported when a wildcard is used.",
                file=sys.stderr,
            )
            return
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("configcache-store", client)

        if len(self._devices) == 1:
            query = CacheQuery(self._service, self._monitor, self._devices[0])
        else:
            query = CacheQuery(self._service, self._monitor)
        include = _get_device_predicate(self._devices)
        for key, ts in store.query_updated(query):
            if not include(key.device):
                continue
            for group in self._groups:
                group.handle_key(key)
                group.handle_timestamp(key, ts)
        for status in store.query_statuses(query):
            if not include(status.key.device):
                continue
            for group in self._groups:
                group.handle_status(status)

        self._format.write(
            *(group for group in sorted(self._groups, key=lambda x: x.order))
        )


def _get_device_predicate(devices):
    if len(devices) < 2:
        return lambda _: True
    return lambda x: next((True for d in devices if x == d), False)
