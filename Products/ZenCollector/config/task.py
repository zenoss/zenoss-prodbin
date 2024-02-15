##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""
The config module provides the implementation of the IConfigurationProxy
interface used within Zenoss Core. This implementation provides basic
configuration retrieval services directly from a remote ZenHub service.
"""

import itertools
import logging
import time

from metrology import Metrology
from twisted.internet import defer
from zope.component import getUtility, queryUtility
from zope.interface import implementer

from Products.ZenHub.PBDaemon import HubDown
from Products.ZenUtils.observable import ObservableMixin

from ..tasks import TaskStates
from ..interfaces import (
    ICollector,
    IDataService,
    IEventService,
    IScheduledTask,
    IFrameworkFactory,
)

log = logging.getLogger("zen.collector.config")


@implementer(IScheduledTask)
class ConfigurationLoaderTask(ObservableMixin):
    """
    Periodically retrieves collector configuration via the
    IConfigurationProxy service.
    """

    STATE_CONNECTING = "CONNECTING"
    STATE_FETCH_MISC_CONFIG = "FETCHING_MISC_CONFIG"
    STATE_FETCH_DEVICE_CONFIG = "FETCHING_DEVICE_CONFIG"
    STATE_PROCESS_DEVICE_CONFIG = "PROCESSING_DEVICE_CONFIG"

    def __init__(
        self,
        name,
        configId=None,
        scheduleIntervalSeconds=None,
        taskConfig=None,
    ):
        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")

        super(ConfigurationLoaderTask, self).__init__()

        self._fetchConfigTimer = Metrology.timer("collectordaemon.configs")

        # Needed for interface
        self.name = name
        self.configId = configId if configId else name
        self.state = TaskStates.STATE_IDLE

        self._dataService = queryUtility(IDataService)
        self._eventService = queryUtility(IEventService)

        self._prefs = taskConfig
        self.interval = self._prefs.configCycleInterval * 60
        self.options = self._prefs.options

        self._collector = getUtility(ICollector)
        self._collector.heartbeatTimeout = self.options.heartbeatTimeout
        log.debug(
            "heartbeat timeout set to %ds", self._collector.heartbeatTimeout
        )

        frameworkFactory = queryUtility(
            IFrameworkFactory, self._collector.frameworkFactoryName
        )
        self._configProxy = frameworkFactory.getConfigurationProxy()

        self.startDelay = 0

    @defer.inlineCallbacks
    def doTask(self):
        """
        Contact zenhub and gather configuration data.

        @return: A task to gather configs
        @rtype: Twisted deferred object
        """
        log.debug("%s gathering configuration", self.name)
        self.startTime = time.time()

        proxy = self._configProxy
        try:
            propertyItems = yield proxy.getPropertyItems()
            self._processPropertyItems(propertyItems)

            thresholdClasses = yield proxy.getThresholdClasses()
            self._processThresholdClasses(thresholdClasses)

            thresholds = yield proxy.getThresholds()
            self._processThresholds(thresholds)

            yield self._collector.runPostConfigTasks()
        except Exception as ex:
            log.exception("task '%s' failed", self.name)

            # stop if a single device was requested and nothing found
            if self.options.device or not self.options.cycle:
                self._collector.stop()

            if isinstance(ex, HubDown):
                # Allow the loader to be reaped and re-added
                self.state = TaskStates.STATE_COMPLETED

    def _processPropertyItems(self, propertyItems):
        log.debug("processing received property items")
        self.state = self.STATE_FETCH_MISC_CONFIG
        if propertyItems:
            self._collector._setCollectorPreferences(propertyItems)

    def _processThresholdClasses(self, thresholdClasses):
        log.debug("processing received threshold classes")
        if thresholdClasses:
            self._collector.loadThresholdClasses(thresholdClasses)

    def _processThresholds(self, thresholds):
        log.debug("processing received thresholds")
        if thresholds:
            self._collector._configureThresholds(thresholds)

    def cleanup(self):
        pass  # Required by interface


class DeviceConfigLoader(object):
    """Handles retrieving devices from the ConfigCache service."""

    def __init__(self, options, proxy, callback):
        self._options = options
        self._proxy = proxy
        self._callback = callback
        self._deviceIds = set([options.device] if options.device else [])
        self._changes_since = 0

    @property
    def deviceIds(self):
        return self._deviceIds

    @defer.inlineCallbacks
    def __call__(self):
        try:
            next_time = time.time()
            config_data = yield self._proxy.getConfigProxies(
                self._changes_since, self._deviceIds
            )
            yield self._processConfigs(config_data)
            self._changes_since = next_time
        except Exception:
            log.exception("failed to retrieve device configs")

    @defer.inlineCallbacks
    def _processConfigs(self, config_data):
        new = config_data.get("new", [])
        updated = config_data.get("updated", [])
        removed = config_data.get("removed", [])
        try:
            try:
                if self._options.device:
                    config = self._get_specified_config(new, updated)
                    if not config:
                        log.error(
                            "configuration for %s unavailable -- "
                            "is that the correct name?",
                            self._options.device,
                        )
                        defer.returnValue(None)
                    new = [config]
                    updated = []
                    removed = []

                yield self._callback(new, updated, removed)
            finally:
                self._update_local_cache(new, updated, removed)
                lengths = (len(new), len(updated), len(removed))
                logmethod = log.debug if lengths == (0, 0, 0) else log.info
                logmethod(
                    "processed %d new, %d updated, and %d removed "
                    "device configs",
                    *lengths
                )
        except Exception:
            log.exception("failed to process device configs")

    def _get_specified_config(self, new, updated):
        return next(
            (
                cfg
                for cfg in itertools.chain(new, updated)
                if self._options.device == cfg.configId
            ),
            None
        )

    def _update_local_cache(self, new, updated, removed):
        self._deviceIds.difference_update(removed)
        self._deviceIds.update(cfg.id for cfg in new)
