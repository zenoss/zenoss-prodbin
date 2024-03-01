##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function, absolute_import

import gc
import logging
import time

from Products.AdvancedQuery import And, Eq
from zenoss.modelindex import constants
from zope.component import createObject

import Products.ZenCollector.configcache as CONFIGCACHE_MODULE

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from .app import Application
from .app.args import get_subparser
from .cache import CacheKey, CacheQuery, ConfigStatus
from .debug import Debug as DebugCommand
from .modelchange import InvalidationCause
from .propertymap import DevicePropertyMap
from .task import BuildConfigTaskDispatcher
from .utils import getConfigServices, RelStorageInvalidationPoller

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
            self.ctx.db.storage, self.ctx.dmd
        )
        self.log.info(
            "polling for device changes every %s seconds", self.interval
        )
        while not self.ctx.controller.shutdown:
            self.ctx.session.sync()
            gc.collect()
            result = poller.poll()
            if result:
                self.log.debug("found %d relevant invalidations", len(result))
                self._process_all(result)
            self.ctx.controller.wait(self.interval)

    def _synchronize(self):
        tool = IModelCatalogTool(self.ctx.dmd)
        # TODO: if device changed monitors, the config should be same (?)
        #       so just rekey the config?
        count = _removeDeleted(self.log, tool, self.store)
        if count == 0:
            self.log.info("no dangling configurations found")
        timelimitmap = DevicePropertyMap.make_build_timeout_map(
            self.ctx.dmd.Devices
        )
        new_devices = _addNew(
            self.log, tool, timelimitmap, self.store, self.dispatcher
        )
        if len(new_devices) == 0:
            self.log.info("no missing configurations found")

    def _process_all(self, invalidations):
        buildlimit_map = DevicePropertyMap.make_build_timeout_map(
            self.ctx.dmd.Devices
        )
        minttl_map = DevicePropertyMap.make_minimum_ttl_map(
            self.ctx.dmd.Devices
        )
        for invalidation in invalidations:
            uid = invalidation.device.getPrimaryId()
            buildlimit = buildlimit_map.get(uid)
            minttl = minttl_map.get(uid)
            try:
                self._process(invalidation, buildlimit, minttl)
            except AttributeError:
                self.log.info(
                    "invalidation  device=%s reason=%s",
                    invalidation.device,
                    invalidation.reason,
                )
                self.log.exception("failed while processing invalidation")

    def _process(self, invalidation, buildlimit, minttl):
        device = invalidation.device
        reason = invalidation.reason
        monitor = device.getPerformanceServerName()
        if monitor is None:
            self.log.warn(
                "ignoring invalidated device having undefined collector  "
                "device=%s reason=%s",
                device,
                reason,
            )
            return
        keys = tuple(
            self.store.search(CacheQuery(monitor=monitor, device=device.id))
        )
        if not keys:
            self._new_device(device, monitor, buildlimit)
        elif reason is InvalidationCause.Updated:
            self._updated_device(device, monitor, keys, minttl)
        elif reason is InvalidationCause.Removed:
            self._removed_device(keys)
        else:
            self.log.warn(
                "ignored unexpected reason  "
                "reason=%s device=%s collector=%s device-oid=%r",
                reason,
                device,
                monitor,
                invalidation.oid,
            )

    def _new_device(self, device, monitor, buildlimit):
        # Don't dispatch jobs if there're any statuses.
        keys = tuple(
            CacheKey(svcname, monitor, device.id)
            for svcname in self.dispatcher.service_names
        )
        for key in keys:
            status = self.store.get_status(key)
            if status is not None:
                self.log.debug(
                    "build jobs already submitted for new device  "
                    "device=%s collector=%s",
                    device,
                    monitor,
                )
                return
        now = time.time()
        for key in keys:
            self.store.set_pending((key, now))
        self.dispatcher.dispatch_all(monitor, device.id, buildlimit)
        self.log.info(
            "submitted build jobs for new device  device=%s collector=%s",
            device,
            monitor,
        )

    def _updated_device(self, device, monitor, keys, minttl):
        statuses = tuple(
            status
            for status in self.store.get_status(*keys)
            if isinstance(status, ConfigStatus.Current)
        )
        now = time.time()
        limit = now - minttl
        retired = set(
            status.key for status in statuses if status.updated >= limit
        )
        expired = set(
            status.key for status in statuses if status.key not in retired
        )
        now = time.time()
        self.store.set_retired(*((key, now) for key in retired))
        self.store.set_expired(*((key, now) for key in expired))
        for key in retired:
            self.log.info(
                "retired configuration of changed device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )
        for key in expired:
            self.log.info(
                "expired configuration of changed device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
            )

    def _removed_device(self, keys):
        self.store.remove(*keys)
        for key in keys:
            self.log.info(
                "removed configuration of deleted device  "
                "device=%s collector=%s service=%s",
                key.device,
                key.monitor,
                key.service,
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
            "device=%s collector=%s service=%s",
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
        if brain.collector is None:
            log.warn(
                "ignoring device having undefined collector  device=%s uid=%s",
                brain.id,
                brain.uid,
            )
            continue
        keys = tuple(
            store.search(CacheQuery(monitor=brain.collector, device=brain.id))
        )
        if not keys:
            timeout = timelimitmap.get(brain.uid)
            dispatcher.dispatch_all(brain.collector, brain.id, timeout)
            log.info(
                "submitted build jobs for device without any configurations  "
                "uid=%s collector=%s",
                brain.uid,
                brain.collector,
            )
            new_devices.append(brain.id)
    return new_devices
