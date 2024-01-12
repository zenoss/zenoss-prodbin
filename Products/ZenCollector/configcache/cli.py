##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import argparse

from datetime import datetime

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from .app import initialize_environment
from .cache import ConfigQuery, ConfigStatus
from .misc.args import get_subparser


class List_(object):

    description = "List configurations"

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "list",
            List_.description,
            parent=_get_common_parser(),
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
            choices=("current", "expired", "pending", "building"),
            default=argparse.SUPPRESS,
            help="Only list configurations having these states.  One or "
            "more states may be specified, separated by commas.",
        )
        subp.set_defaults(factory=List_)

    def __init__(self, args):
        self._monitor = args.monitor
        self._service = args.service
        self._showuid = args.show_uid
        state_names = getattr(args, "states", ())
        if state_names:
            states = set()
            for name in state_names:
                states.add(_name_state_lookup[name])
            self._states = tuple(states)
        else:
            self._states = ()

    def run(self):
        initialize_environment()
        client = getRedisClient(url=getRedisUrl())
        store = createObject("configcache-store", client)
        query = ConfigQuery(service=self._service, monitor=self._monitor)
        results = store.get_status(*store.search(query))
        if self._states:
            results = (
                (key, status)
                for key, status in results
                if isinstance(status, self._states)
            )
        rows = []
        maxd, maxs, maxm = 0, 0, 0
        for key, status in sorted(
            results, key=lambda x: (x[0].device, x[0].service)
        ):
            if self._showuid:
                uid = store.get_uid(key.device)
            else:
                uid = key.device
            status_text = _format_status(status)
            maxd = max(maxd, len(uid))
            maxs = max(maxs, len(status_text))
            maxm = max(maxm, len(key.monitor))
            rows.append((uid, status_text, key.monitor, key.service))
        if rows:
            print(
                "{0:{maxd}} {1:{maxs}} {2:{maxm}} {3}".format(
                    "DEVICE",
                    "STATUS",
                    "MONITOR",
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
    "expired": ConfigStatus.Expired,
    "pending": ConfigStatus.Pending,
    "building": ConfigStatus.Building,
}


def _format_status(status):
    if isinstance(status, ConfigStatus.Current):
        return "last updated {}".format(_format_date(status.updated))
    elif isinstance(status, ConfigStatus.Expired):
        return "expired"
    elif isinstance(status, ConfigStatus.Pending):
        return "build request submitted {}".format(
            _format_date(status.submitted)
        )
    elif isinstance(status, ConfigStatus.Building):
        return "building started {}".format(_format_date(status.started))
    else:
        return "????"


def _format_date(ts):
    when = datetime.fromtimestamp(ts)
    return when.strftime("%Y-%m-%d %H:%M:%S")


class Show(object):

    description = "Show a configuration (JSON)"

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(subparsers, "show", "Show a configuration (JSON)")
        subp.add_argument(
            "service", nargs=1, help="name of the configuration service"
        )
        subp.add_argument(
            "monitor", nargs=1, help="name of the performance monitor"
        )
        subp.add_argument("device", nargs=1, help="name of the device")
        subp.set_defaults(factory=Show)

    def __init__(self, args):
        pass

    def run(self):
        pass


class Expire(object):

    description = ""

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "expire",
            "Mark configurations as expired",
            parent=_get_common_parser(),
        )
        subp.set_defaults(factory=Expire)

    def __init__(self, args):
        pass

    def run(self):
        pass


# list - list configs;
#      ls [-m monitor] [-s service] [-u] [-f state] [device]
#      where 'monitor', 'service' and 'device' can be globs.
#      Output should look like:
#      [device] [state] [monitor] [service]
#      if '-u' is given, then
#      [device-path] [state] [monitor] [service]
#      where 'state' is:
#          Current HH:MM:SS  - current with time remaining
#          Expired           - expired configuration
#          Pending HH:MM:SS  - pending with time remaining
#      and 'device-path' is the dmd path (UID)
#
# show - show config in JSON format;
#       cat [service] [monitor] [device]
#       No wildcard support.
#
# expire - Mark one or more configurations expired;
#          expire [-m monitor] [-s service] [device]


class MultiChoice(argparse.Action):
    """Allow multiple values for a choice option."""

    def __init__(self, option_strings, dest, **kwargs):
        kwargs["type"] = self._split_listed_choices
        super(MultiChoice, self).__init__(option_strings, dest, **kwargs)

    @property
    def choices(self):
        return self._choices_checker

    @choices.setter
    def choices(self, values):
        self._choices_checker = _ChoicesChecker(values)

    def _split_listed_choices(self, value):
        if "," in value:
            return tuple(value.split(","))
        return value

    def __call__(self, parser, namespace, values=None, option_string=None):
        if isinstance(values, basestring):
            values = (values,)
        setattr(namespace, self.dest, values)


class _ChoicesChecker(object):
    def __init__(self, values):
        self._choices = values

    def __contains__(self, value):
        if isinstance(value, (list, tuple)):
            return all(v in self._choices for v in value)
        else:
            return value in self._choices

    def __iter__(self):
        return iter(self._choices)


_common_parser = None


def _get_common_parser():
    global _common_parser
    if _common_parser is None:
        _common_parser = argparse.ArgumentParser(add_help=False)
        _common_parser.add_argument(
            "-m",
            "--monitor",
            type=str,
            default="*",
            help="Name of the performance monitor.  Supports simple '*' "
            "wildcard comparisons.  A lone '*' selects all monitors.",
        )
        _common_parser.add_argument(
            "-s",
            "--service",
            type=str,
            default="*",
            help="Name of the configuration service.  Supports simple '*' "
            "wildcard comparisons.  A lone '*' selects all services.",
        )
        _common_parser.add_argument(
            "device",
            nargs="*",
            default=argparse.SUPPRESS,
            help="Name of the device.  Multiple devices may be specified. "
            "Supports simple '*' wildcard comparisons. Not specifying a "
            "device will select all devices.",
        )
    return _common_parser
