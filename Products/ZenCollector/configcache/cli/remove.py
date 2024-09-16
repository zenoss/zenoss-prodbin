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

from zope.component import createObject

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl

from ..app import initialize_environment
from ..app.args import get_subparser
from ..cache import DeviceQuery

from .args import get_devargs_parser
from ._selection import get_message, confirm


class RemoveOidMap(object):

    description = "Remove oidmap configuration from the cache"
    configs = (("store.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "oidmap",
            description=RemoveOidMap.description,
        )
        subp.set_defaults(factory=RemoveOidMap)

    def __init__(self, args):
        pass

    def run(self):
        initialize_environment(configs=self.configs, useZope=False)
        client = getRedisClient(url=getRedisUrl())
        store = createObject("oidmapcache-store", client)
        status = store.get_status()
        if status is None:
            print("No oidmap configuration found in the cache")
        else:
            store.remove()
            print("Oidmap configuration removed from the cache")


class RemoveDevice(object):

    description = "Delete device configurations from the cache"
    configs = (("store.zcml", __name__),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers,
            "remove",
            description=RemoveDevice.description,
            parent=get_devargs_parser(),
        )
        subp.set_defaults(factory=RemoveDevice)

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
        store = createObject("deviceconfigcache-store", client)
        query = DeviceQuery(service=self._service, monitor=self._monitor)
        results = store.query_statuses(query)
        method = self._no_devices if not self._devices else self._with_devices
        keys = method(results, wildcard=haswildcard)
        store.remove(*keys)
        count = len(keys)
        print(
            "deleted %d device configuration%s"
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
        mesg = get_message("Delete", self._monitor, self._service)
        return confirm(mesg)
