##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import argparse
import sys

from datetime import datetime

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..app import initialize_environment
from ..app.args import get_subparser
from ..cache import CacheQuery, ConfigStatus

from .args import get_common_parser, MultiChoice


class List_(object):

    description = "List configurations"

    configs = (("list.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "list",
            description=List_.description,
            parent=get_common_parser(),
        )
        subp.add_argument(
            "-u",
            dest="show_uid",
            default=False,
            action="store_true",
            help="Display ZODB path for device",
        )
        subp.add_argument(
            "-f",
            dest="states",
            action=MultiChoice,
            choices=("current", "retired", "expired", "pending", "building"),
            default=argparse.SUPPRESS,
            help="Only list configurations having these states.  One or "
            "more states may be specified, separated by commas.",
        )
        subp.set_defaults(factory=List_)

    def __init__(self, args):
        self._monitor = "*{}*".format(args.collector).replace("***", "*")
        self._service = "*{}*".format(args.service).replace("***", "*")
        self._showuid = args.show_uid
        self._devices = getattr(args, "device", [])
        state_names = getattr(args, "states", ())
        if state_names:
            states = set()
            for name in state_names:
                states.add(_name_state_lookup[name])
            self._states = tuple(states)
        else:
            self._states = ()

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
        if haswildcard:
            query = CacheQuery(
                service=self._service,
                monitor=self._monitor,
                device=self._devices[0],
            )
        elif len(self._devices) == 1:
            query = CacheQuery(
                service=self._service,
                monitor=self._monitor,
                device=self._devices[0],
            )
        else:
            query = CacheQuery(service=self._service, monitor=self._monitor)
        data = store.get_statuses(query)
        if self._states:
            data = (
                status for status in data if isinstance(status, self._states)
            )
        if len(self._devices) > 1:
            data = (
                status
                for status in data
                if status.key.device in self._devices
            )
        rows = []
        maxd, maxs, maxm = 1, 1, 1
        for status in sorted(
            data, key=lambda x: (x.key.device, x.key.service)
        ):
            if self._showuid:
                devid = status.uid or status.key.device
            else:
                devid = status.key.device
            status_text = _format_status(status)
            maxd = max(maxd, len(devid))
            maxs = max(maxs, len(status_text))
            maxm = max(maxm, len(status.key.monitor))
            rows.append(
                (devid, status_text, status.key.monitor, status.key.service)
            )
        if rows:
            print(
                "{0:{maxd}} {1:{maxs}} {2:{maxm}} {3}".format(
                    "DEVICE",
                    "STATUS",
                    "COLLECTOR",
                    "SERVICE",
                    maxd=maxd,
                    maxs=maxs,
                    maxm=maxm,
                )
            )
        for row in rows:
            print(
                "{0:{maxd}} {1:{maxs}} {2:{maxm}} {3}".format(
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    maxd=maxd,
                    maxs=maxs,
                    maxm=maxm,
                )
            )


_name_state_lookup = {
    "current": ConfigStatus.Current,
    "retired": ConfigStatus.Retired,
    "expired": ConfigStatus.Expired,
    "pending": ConfigStatus.Pending,
    "building": ConfigStatus.Building,
}


def _format_status(status):
    if isinstance(status, ConfigStatus.Current):
        return "current since {}".format(_format_date(status.updated))
    elif isinstance(status, ConfigStatus.Retired):
        return "retired since {}".format(_format_date(status.retired))
    elif isinstance(status, ConfigStatus.Expired):
        return "expired since {}".format(_format_date(status.expired))
    elif isinstance(status, ConfigStatus.Pending):
        return "waiting to build since {}".format(
            _format_date(status.submitted)
        )
    elif isinstance(status, ConfigStatus.Building):
        return "build started {}".format(_format_date(status.started))
    else:
        return "????"


def _format_date(ts):
    when = datetime.fromtimestamp(ts)
    return when.strftime("%Y-%m-%d %H:%M:%S")
