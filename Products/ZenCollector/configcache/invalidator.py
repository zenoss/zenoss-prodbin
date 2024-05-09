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

from multiprocessing import Process

from zenoss.modelindex import constants
from zope.component import createObject

import Products.ZenCollector.configcache as CONFIGCACHE_MODULE

from Products.ZenUtils.RedisUtils import getRedisClient, getRedisUrl
from Products.Zuul.catalog.interfaces import IModelCatalogTool

from .app import Application
from .app.args import get_subparser
from .cache import CacheQuery
from .debug import Debug as DebugCommand
from .dispatcher import BuildConfigTaskDispatcher
from .handlers import (
    NewDeviceHandler,
    DeviceUpdateHandler,
    MissingConfigsHandler,
    RemoveConfigsHandler,
)
from .modelchange import InvalidationCause
from .utils import (
    get_build_timeout,
    get_minimum_ttl,
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
            subparsers, "invalidator", description=Invalidator.description
        )
        subsubparsers = subp.add_subparsers(title="Invalidator Commands")

        subp_run = get_subparser(
            subsubparsers, "run", description="Run the invalidator service"
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
            description=(
                "Signal the invalidator service to toggle debug logging"
            ),
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

        self._process = _InvalidationProcessor(
            self.log, self.store, self.dispatcher
        )

        self.interval = config["poll-interval"]

    def run(self):
        # Handle changes that occurred when Invalidator wasn't running.
        self._synchronize()

        poller = RelStorageInvalidationPoller(
            self.ctx.db.storage, self.ctx.dmd
        )
        self.log.info(
            "polling for device changes every %s seconds", self.interval
        )
        while not self.ctx.controller.shutdown:
            try:
                self.ctx.session.sync()
                invalidations = poller.poll()
                if not invalidations:
                    continue
                self._process_invalidations(invalidations)
            finally:
                # Call cacheGC to aggressively trim the ZODB cache
                self.ctx.session.cacheGC()
                self.ctx.controller.wait(self.interval)

    def _synchronize(self):
        sync_process = Process(
            target=_synchronize_cache,
            args=(self.log, self.ctx.dmd, self.dispatcher),
        )
        sync_process.start()
        sync_process.join()  # blocks until subprocess has exited

    def _process_invalidations(self, invalidations):
        self.log.debug("found %d relevant invalidations", len(invalidations))
        for inv in invalidations:
            try:
                self._process(inv.device, inv.oid, inv.reason)
            except Exception:
                self.log.exception(
                    "failed to process invalidation  device=%s",
                    inv.device,
                )


_solr_fields = ("id", "collector", "uid")


def _synchronize_cache(log, dmd, dispatcher):
    store = createObject(
        "configcache-store", getRedisClient(url=getRedisUrl())
    )
    tool = IModelCatalogTool(dmd)
    catalog_results = tool.cursor_search(
        types=("Products.ZenModel.Device.Device",),
        limit=constants.DEFAULT_SEARCH_LIMIT,
        fields=_solr_fields,
    ).results
    devices = {
        (brain.id, brain.collector): brain.uid
        for brain in catalog_results
        if brain.collector is not None
    }
    _removeDeleted(log, store, devices)
    _addNewOrChangedDevices(log, store, dispatcher, dmd, devices)


def _removeDeleted(log, store, devices):
    """
    Remove deleted devices from the cache.

    @param devices: devices that currently exist
    @type devices: Mapping[Sequence[str, str], str]
    """
    devices_not_found = tuple(
        key
        for key in store.search()
        if (key.device, key.monitor) not in devices
    )
    if devices_not_found:
        RemoveConfigsHandler(log, store)(devices_not_found)
    else:
        log.info("no dangling configurations found")


def _addNewOrChangedDevices(log, store, dispatcher, dmd, devices):
    # Add new devices to the config and metadata store.
    # Also look for device that have changed their device class.
    # Query the catalog for all devices
    new_devices = 0
    changed_devices = 0
    handle = NewDeviceHandler(log, store, dispatcher)
    for (deviceId, monitorId), uid in devices.iteritems():
        try:
            device = dmd.unrestrictedTraverse(uid)
        except Exception as ex:
            log.warning(
                "failed to get device  error-type=%s error=%s uid=%s",
                type(ex),
                ex,
                uid,
            )
            continue
        timeout = get_build_timeout(device)
        keys_with_configs = tuple(
            store.search(CacheQuery(monitor=monitorId, device=deviceId))
        )
        uid = device.getPrimaryId()
        if not keys_with_configs:
            handle(deviceId, monitorId, timeout)
            new_devices += 1
        else:
            current_uid = store.get_uid(deviceId)
            # A device with a changed device class will have a different uid.
            if current_uid != uid:
                handle(deviceId, monitorId, timeout, False)
                changed_devices += 1
    if new_devices == 0:
        log.info("no missing configurations found")
    if changed_devices == 0:
        log.info("no devices with a different device class found")


class _InvalidationProcessor(object):

    def __init__(self, log, store, dispatcher):
        self.log = log
        self.store = store
        self._remove = RemoveConfigsHandler(log, store)
        self._update = DeviceUpdateHandler(log, store, dispatcher)
        self._missing = MissingConfigsHandler(log, store, dispatcher)
        self._new = NewDeviceHandler(log, store, dispatcher)

    def __call__(self, device, oid, reason):
        uid = device.getPrimaryId()
        self.log.info("handling device %s", uid)
        buildlimit = get_build_timeout(device)
        minttl = get_minimum_ttl(device)
        monitor = device.getPerformanceServerName()
        if monitor is None:
            self.log.warn(
                "ignoring invalidated device having undefined collector  "
                "device=%s reason=%s",
                device,
                reason,
            )
            return
        keys_with_config = tuple(
            self.store.search(CacheQuery(monitor=monitor, device=device.id))
        )
        if not keys_with_config:
            self._new(device.id, monitor, buildlimit)
        elif reason is InvalidationCause.Updated:
            # Check for device class change
            stored_uid = self.store.get_uid(device.id)
            if uid != stored_uid:
                self._new(device.id, monitor, buildlimit, False)
            else:
                self._update(keys_with_config, minttl)
                self._missing(device.id, monitor, keys_with_config, buildlimit)
        elif reason is InvalidationCause.Removed:
            self._remove(keys_with_config)
        else:
            self.log.warn(
                "ignored unexpected reason  "
                "reason=%s device=%s collector=%s device-oid=%r",
                reason,
                device,
                monitor,
                oid,
            )
