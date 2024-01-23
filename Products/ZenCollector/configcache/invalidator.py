##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import

import logging

from Products.AdvancedQuery import And, Eq
from zenoss.modelindex import constants
from zope.component import createObject

import Products.ZenCollector.configcache as CONFIGCACHE_MODULE

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from .app import Application
from .cache import ConfigQuery
from .debug import Debug as DebugCommand
from .misc.args import get_subparser
from .modelchange import InvalidationCause
from .utils import (
    BuildConfigTaskDispatcher,
    Constants,
    DevicePropertyMap,
    getConfigServices,
    RelStorageInvalidationPoller,
)

_default_interval = 30.0


class Invalidator(object):

    description = (
        "Analyzes changes in ZODB to determine whether to update "
        "device configurations"
    )

    configs = (("modelchange.zcml", CONFIGCACHE_MODULE),)

    @staticmethod
    def add_arguments(parser, subparsers):
        subp = get_subparser(
            subparsers, "invalidator", Invalidator.description
        )
        subsubparsers = subp.add_subparsers(title="Invalidator Commands")

        subp_run = get_subparser(
            subsubparsers, "run", "Run the invalidator service"
        )
        Application.add_all_arguments(subp_run)
        subp_run.add_argument(
            "--poll-interval",
            default=_default_interval,
            type=float,
            help="Invalidation polling interval (in seconds)",
        )
        subp_run.set_defaults(
            factory=Application.from_args,
            parser=subp_run,
            task=Invalidator,
        )

        subp_debug = get_subparser(
            subsubparsers,
            "debug",
            "Signal the invalidator service to toggle debug logging",
        )
        Application.add_pidfile_arguments(subp_debug)
        subp_debug.set_defaults(factory=DebugCommand.from_args)

        Application.add_genconf_command(subsubparsers, (subp_run, subp_debug))

    def __init__(self, config, context):
        self.log = logging.getLogger("zen.configcache.invalidator")
        self.ctx = context

        configClasses = getConfigServices()
        for cls in configClasses:
            self.log.info(
                "using service class %s.%s", cls.__module__, cls.__name__
            )
        self.dispatcher = BuildConfigTaskDispatcher(configClasses)

        client = getRedisClient(url=getRedisUrl())
        self.store = createObject("configcache-store", client)

        self.interval = config["poll-interval"]

    def run(self):
        self._synchronize()

        poller = RelStorageInvalidationPoller(
            self.ctx.db.storage, self.ctx.session, self.ctx.dmd
        )
        self.log.info(
            "polling for device changes every %s seconds", self.interval
        )
        while not self.ctx.controller.shutdown:
            result = poller.poll()
            if result:
                self.log.debug("found %d relevant invalidations", len(result))
            for invalidation in result:
                try:
                    self._process(invalidation)
                except AttributeError:
                    self.log.info(
                        "invalidation  device=%s reason=%s",
                        invalidation.device,
                        invalidation.reason,
                    )
                    self.log.exception("failed while processing invalidation")
            self.ctx.controller.wait(self.interval)

    def _synchronize(self):
        tool = IModelCatalogTool(self.ctx.dmd)
        # TODO: if device changed monitors, the config should be same (?)
        #       so just rekey the config?
        count = _removeDeleted(self.log, tool, self.store)
        if count == 0:
            self.log.info("no dangling configurations found")
        timelimitmap = DevicePropertyMap.from_organizer(
            self.ctx.dmd.Devices, Constants.build_timeout_id
        )
        new_devices = _addNew(
            self.log, tool, timelimitmap, self.store, self.dispatcher
        )
        if len(new_devices) == 0:
            self.log.info("no missing configurations found")

    def _process(self, invalidation):
        device = invalidation.device
        reason = invalidation.reason
        monitor = device.getPerformanceServerName()
        keys = list(
            self.store.search(ConfigQuery(monitor=monitor, device=device.id))
        )
        if not keys:
            timelimitmap = DevicePropertyMap.from_organizer(
                self.ctx.dmd.Devices, Constants.build_timeout_id
            )
            uid = device.getPrimaryId()
            timeout = timelimitmap.get(uid)
            self.dispatcher.dispatch_all(monitor, device.id, timeout)
            self.log.info(
                "submitted build jobs for new device  uid=%s monitor=%s",
                uid,
                monitor,
            )
        elif reason is InvalidationCause.Updated:
            self.store.set_expired(*keys)
            for key in keys:
                self.log.info(
                    "expired configuration of changed device  "
                    "device=%s monitor=%s service=%s device-oid=%r",
                    key.device,
                    key.monitor,
                    key.service,
                    invalidation.oid,
                )
        elif reason is InvalidationCause.Removed:
            self.store.remove(*keys)
            for key in keys:
                self.log.info(
                    "removed configuration of deleted device  "
                    "device=%s monitor=%s service=%s device-oid=%r",
                    key.device,
                    key.monitor,
                    key.service,
                    invalidation.oid,
                )
        else:
            self.log.warn(
                "ignored unexpected reason  "
                "reason=%s device=%s monitor=%s device-oid=%r",
                reason,
                device,
                monitor,
                invalidation.oid,
            )


_solr_fields = ("id", "collector", "uid")


def _deviceExistsInCatalog(tool, monitorId, deviceId):
    query = And(Eq("id", deviceId), Eq("collector", monitorId))
    brain = next(
        iter(tool.search_model_catalog(query, fields=_solr_fields)), None
    )
    return brain is not None


def _removeDeleted(log, tool, store):
    # Remove deleted devices from the config and metadata store.
    devices_not_found = tuple(
        key
        for key in store.search()
        if not _deviceExistsInCatalog(tool, key.monitor, key.device)
    )
    store.remove(*devices_not_found)
    for key in devices_not_found:
        log.info(
            "removed configuration for deleted device  "
            "device=%s monitor=%s service=%s",
            key.device,
            key.monitor,
            key.service,
        )
    return len(devices_not_found)


def _addNew(log, tool, timelimitmap, store, dispatcher):
    # Add new devices to the config and metadata store.
    # Query the catalog for all devices
    catalog_results = tool.cursor_search(
        types=("Products.ZenModel.Device.Device",),
        limit=constants.DEFAULT_SEARCH_LIMIT,
        fields=_solr_fields,
    ).results
    new_devices = []
    for brain in catalog_results:
        keys = tuple(
            store.search(ConfigQuery(monitor=brain.collector, device=brain.id))
        )
        if not keys:
            timeout = timelimitmap.get(brain.uid)
            dispatcher.dispatch_all(brain.collector, brain.id, timeout)
            log.info(
                "submitted build jobs for device without any configurations  "
                "uid=%s monitor=%s",
                brain.uid,
                brain.collector,
            )
            new_devices.append(brain.id)
    return new_devices