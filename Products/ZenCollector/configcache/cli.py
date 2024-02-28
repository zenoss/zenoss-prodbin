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
import os
import sys
import time

from datetime import datetime

import six

from IPython.lib import pretty
from twisted.spread.jelly import unjellyableRegistry
from zope.component import createObject

import Products.ZenCollector.configcache as CONFIGCACHE_MODULE

from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl
from Products.ZenUtils.terminal_size import get_terminal_size

from .app import initialize_environment
from .app.args import get_subparser
from .cache import ConfigQuery, ConfigStatus


class List_(object):

    description = "List configurations"

    configs = (("list.zcml", CONFIGCACHE_MODULE),)

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
            choices=("current", "retired", "expired", "pending", "building"),
            default=argparse.SUPPRESS,
            help="Only list configurations having these states.  One or "
            "more states may be specified, separated by commas.",
        )
        subp.set_defaults(factory=List_)

    def __init__(self, args):
        self._monitor = "*{}*".format(args.monitor).replace("***", "*")
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
            query = ConfigQuery(
                service=self._service,
                monitor=self._monitor,
                device=self._devices[0],
            )
        else:
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
        if len(self._devices) > 0:
            data = (key for key in results if key[0].device in self._devices)
        else:
            data = results
        for key, status in sorted(
            data, key=lambda x: (x[0].device, x[0].service)
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
    "retired": ConfigStatus.Retired,
    "expired": ConfigStatus.Expired,
    "pending": ConfigStatus.Pending,
    "building": ConfigStatus.Building,
}


def _format_status(status):
    if isinstance(status, ConfigStatus.Current):
        return "last updated {}".format(_format_date(status.updated))
    elif isinstance(status, ConfigStatus.Retired):
        return "retired"
    elif isinstance(status, ConfigStatus.Expired):
        return "expired"
    elif isinstance(status, ConfigStatus.Pending):
        return "build request submitted {}".format(
            _format_date(status.submitted)
        )
    elif isinstance(status, ConfigStatus.Building):
        return "build started {}".format(_format_date(status.started))
    else:
        return "????"


def _format_date(ts):
    when = datetime.fromtimestamp(ts)
    return when.strftime("%Y-%m-%d %H:%M:%S")


class Show(object):

    description = "Show a configuration"

    configs = (("show.zcml", CONFIGCACHE_MODULE),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(subparsers, "show", Show.description)
        termsize = get_terminal_size()
        subp.add_argument(
            "--width",
            type=int,
            default=termsize.columns,
            help="Maxiumum number of columns to use in the output. "
            "By default, this is the width of the terminal",
        )
        subp.add_argument(
            "service", nargs=1, help="name of the configuration service"
        )
        subp.add_argument(
            "monitor", nargs=1, help="name of the performance monitor"
        )
        subp.add_argument("device", nargs=1, help="name of the device")
        subp.set_defaults(factory=Show)

    def __init__(self, args):
        self._monitor = args.monitor[0]
        self._service = args.service[0]
        self._device = args.device[0]
        if _is_output_redirected():
            # when stdout is redirected, default to 79 columns unless
            # the --width option has a non-default value.
            termsize = get_terminal_size()
            if args.width != termsize.columns:
                self._columns = args.width
            else:
                self._columns = 79
        else:
            self._columns = args.width

    def run(self):
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("configcache-store", client)
        results, err = _query_cache(
            store,
            service="*{}*".format(self._service),
            monitor="*{}*".format(self._monitor),
            device="*{}*".format(self._device),
        )
        if results:
            for cls in set(unjellyableRegistry.values()):
                if cls is DeviceProxy:
                    pretty.for_type(cls, _pp_DeviceProxy)
                else:
                    pretty.for_type(cls, _pp_default)
            pretty.pprint(results.config, max_width=self._columns)
        else:
            print(err, file=sys.stderr)


def _query_cache(store, service, monitor, device):
    query = ConfigQuery(service=service, monitor=monitor, device=device)
    results = store.search(query)
    first_key = next(results, None)
    if first_key is None:
        return (None, "configuration not found")
    second_key = next(results, None)
    if second_key is not None:
        return (None, "more than one configuration matched arguments")
    return (store.get(first_key), None)


def _pp_DeviceProxy(obj, p, cycle):
    _printer(
        obj,
        p,
        cycle,
        lambda k, v: v if "password" not in k.lower() else "******",
    )


def _pp_default(obj, p, cycle):
    _printer(obj, p, cycle, lambda k, v: v)


def _printer(obj, p, cycle, vprint):
    clsname = obj.__class__.__name__
    if cycle:
        p.text("<{}: ...>".format(clsname))
    else:
        with p.group(2, "<{}: ".format(clsname), ">"):
            attrs = (
                (k, v)
                for k, v in sorted(obj.__dict__.items(), key=lambda x: x[0])
                if v not in (None, "", {}, [])
            )
            for idx, (k, v) in enumerate(attrs):
                if idx:
                    p.text(",")
                    p.breakable()
                p.text("{}=".format(k))
                p.pretty(vprint(k, v))


class Expire(object):

    description = "Mark configurations as expired"

    configs = (("expire.zcml", CONFIGCACHE_MODULE),)

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
        self._monitor = "*{}*".format(args.monitor).replace("***", "*")
        self._service = "*{}*".format(args.service).replace("***", "*")
        self._devices = getattr(args, "device", [])

    def run(self):
        if not self._confirm_inputs():
            print("exit")
            return
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("configcache-store", client)
        query = ConfigQuery(service=self._service, monitor=self._monitor)
        results = store.get_status(*store.search(query))
        method = self._no_devices if not self._devices else self._with_devices
        keys = method(results)
        now = time.time()
        store.set_expired(*((key, now) for key in keys))
        count = len(keys)
        print(
            "expired %d device configuration%s"
            % (count, "" if count == 1 else "s")
        )

    def _no_devices(self, results):
        return tuple(ident.key for ident, state in results)

    def _with_devices(self, results):
        return tuple(
            ident.key
            for ident, state in results
            if ident.key.device in self._devices
        )

    def _confirm_inputs(self):
        if self._devices:
            return True
        if (self._monitor, self._service) == ("*", "*"):
            mesg = "Recreate all device configurations"
        elif "*" not in self._monitor and self._service == "*":
            mesg = (
                "Recreate all device configurations monitored by the "
                "'%s' collector" % (self._monitor,)
            )
        elif "*" in self._monitor and self._service == "*":
            mesg = (
                "Recreate all device configurations monitored by all "
                "collectors matching '%s'" % (self._monitor,)
            )
        elif self._monitor == "*" and "*" not in self._service:
            mesg = (
                "Recreate all device configurations created by the '%s' "
                "configuration service" % (self._service.split(".")[-1],)
            )
        elif self._monitor == "*" and "*" in self._service:
            mesg = (
                "Recreate all device configurations created by all "
                "configuration services matching '%s'" % (self._service,)
            )
        elif "*" in self._monitor and "*" not in self._service:
            mesg = (
                "Recreate all device configurations created by the "
                "'%s' configuration service and monitored by all "
                "collectors matching '%s'" % (self._service, self._monitor)
            )
        elif "*" not in self._monitor and "*" in self._service:
            mesg = (
                "Recreate all device configurations monitored by the '%s' "
                "collector and created by all configuration services "
                "matching '%s'" % (self._monitor, self._service)
            )
        elif "*" not in self._monitor and "*" not in self._service:
            mesg = (
                "Recreate all device configurations monitored by the '%s' "
                "collector and created by the '%s' configuration service"
                % (self._monitor, self._service)
            )
        elif "*" in self._monitor and "*" in self._service:
            mesg = (
                "Recreate all device configurations monitored by all "
                "collectors matching '%s' and created by all configuration "
                "services matching '%s'" % (self._monitor, self._service)
            )
        else:
            mesg = "monitor '%s'  service '%s'" % (
                self._monitor,
                self._service,
            )
        return _confirm(mesg)


def _confirm(mesg):
    response = None
    while response not in ["y", "n", ""]:
        response = six.moves.input(
            "%s. Are you sure (y/N)? " % (mesg,)
        ).lower()
    return response == "y"


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
        if isinstance(values, six.string_types):
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


def _is_output_redirected():
    return os.fstat(0) != os.fstat(1)


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
