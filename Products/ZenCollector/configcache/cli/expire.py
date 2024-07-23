##############################################################################
#
# Copyright (C) Zenoss, Inc. 2024, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import, print_function

import sys
import time

import six

from zope.component import createObject

from Products.ZenUtils.init import initialize_environment
from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..app.args import get_subparser
from ..cache import CacheQuery

from .args import get_common_parser


class Expire(object):

    description = "Mark configurations as expired"

    configs = (("expire.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "expire",
            description=Expire.description,
            parent=get_common_parser(),
        )
        subp.set_defaults(factory=Expire)

    def __init__(self, args):
        self._monitor = args.collector
        self._service = args.service
        self._devices = getattr(args, "device", [])

    def run(self):
        haswildcard = any("*" in d for d in self._devices)
        if haswildcard:
            if len(self._devices) > 1:
                print(
                    "Only one DEVICE argument supported when a "
                    "wildcard is used.",
                    file=sys.stderr,
                )
                return
            else:
                self._devices = self._devices[0].replace("*", "")
        if not self._confirm_inputs():
            print("exit")
            return
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("configcache-store", client)
        query = CacheQuery(service=self._service, monitor=self._monitor)
        results = store.query_statuses(query)
        method = self._no_devices if not self._devices else self._with_devices
        keys = method(results, wildcard=haswildcard)
        now = time.time()
        store.set_expired(*((key, now) for key in keys))
        count = len(keys)
        print(
            "expired %d device configuration%s"
            % (count, "" if count == 1 else "s")
        )

    def _no_devices(self, results, wildcard=False):
        return tuple(status.key for status in results)

    def _with_devices(self, results, wildcard=False):
        if wildcard:
            predicate = self._check_wildcard
        else:
            predicate = self._check_list

        return tuple(
            status.key for status in results if predicate(status.key.device)
        )

    def _check_wildcard(self, device):
        return self._devices in device

    def _check_list(self, device):
        return device in self._devices

    def _confirm_inputs(self):
        if self._devices:
            return True
        if (self._monitor, self._service) == ("*", "*"):
            mesg = "Recreate all device configurations"
        elif "*" not in self._monitor and self._service == "*":
            mesg = (
                "Recreate all configurations for devices monitored by the "
                "'%s' collector" % (self._monitor,)
            )
        elif "*" in self._monitor and self._service == "*":
            mesg = (
                "Recreate all configurations for devices monitored by all "
                "collectors matching '%s'" % (self._monitor,)
            )
        elif self._monitor == "*" and "*" not in self._service:
            mesg = (
                "Recreate all device configurations created by the '%s' "
                "service" % (self._service.split(".")[-1],)
            )
        elif self._monitor == "*" and "*" in self._service:
            mesg = (
                "Recreate all device configurations created by all "
                "services matching '%s'" % (self._service,)
            )
        elif "*" in self._monitor and "*" not in self._service:
            mesg = (
                "Recreate all configurations created by the '%s' "
                "service for devices monitored by all collectors "
                "matching '%s'" % (self._service, self._monitor)
            )
        elif "*" not in self._monitor and "*" in self._service:
            mesg = (
                "Recreate all configurations for devices monitored by the "
                "'%s' collector and created by all services matching '%s'"
                % (self._monitor, self._service)
            )
        elif "*" not in self._monitor and "*" not in self._service:
            mesg = (
                "Recreate all configurations for devices monitored by the "
                "'%s' collector and created by the '%s' service"
                % (self._monitor, self._service)
            )
        elif "*" in self._monitor and "*" in self._service:
            mesg = (
                "Recreate all configurations device monitored by all "
                "collectors matching '%s' and created by all services "
                "matching '%s'" % (self._monitor, self._service)
            )
        else:
            mesg = "collector '%s'  service '%s'" % (
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
