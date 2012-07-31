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
import logging
log = logging.getLogger("zen.collector.config")
import time

import zope.component
import zope.interface
from twisted.internet import defer
from twisted.python.failure import Failure

from Products.ZenCollector.interfaces import ICollector,\
                                             ICollectorPreferences,\
                                             IFrameworkFactory,\
                                             IConfigurationProxy,\
                                             IScheduledTask,\
                                             IDataService,\
                                             IEventService
from Products.ZenCollector.tasks import TaskStates
from Products.ZenUtils.observable import ObservableMixin
from Products.ZenHub.PBDaemon import HubDown


class ConfigurationProxy(object):
    """
    This implementation of IConfigurationProxy provides basic configuration
    retrieval from the remote ZenHub instance using the remote configuration
    service proxy as specified by the collector's configuration.
    """
    zope.interface.implements(IConfigurationProxy)

    def getPropertyItems(self, prefs):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        # Load any configuration properties for this daemon
        log.debug("Fetching daemon configuration properties")
        d = serviceProxy.callRemote('getConfigProperties')
        d.addCallback(lambda result: dict(result))
        return d

    def getThresholdClasses(self, prefs):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        log.debug("Fetching threshold classes")
        d = serviceProxy.callRemote('getThresholdClasses')
        return d

    def getThresholds(self, prefs):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        log.debug("Fetching collector thresholds")
        d = serviceProxy.callRemote('getCollectorThresholds')
        return d

    def getConfigProxies(self, prefs, ids=[]):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        log.debug("Fetching configurations")
        d = serviceProxy.callRemote('getDeviceConfigs', ids)
        return d

    def deleteConfigProxy(self, prefs, id):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        # not implemented in the basic ConfigurationProxy
        return defer.succeed(None)

    def updateConfigProxy(self, prefs, config):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        # not implemented in the basic ConfigurationProxy
        return defer.succeed(None)

    def getConfigNames(self, result, prefs):
        if not ICollectorPreferences.providedBy(prefs):
            raise TypeError("config must provide ICollectorPreferences")

        self._collector = zope.component.queryUtility(ICollector)
        serviceProxy = self._collector.getRemoteConfigServiceProxy()

        log.debug("Fetching device names")
        d = serviceProxy.callRemote('getDeviceNames')
        return d


class ConfigurationLoaderTask(ObservableMixin):
    """
    A task that periodically retrieves collector configuration via the 
    IConfigurationProxy service.
    """
    zope.interface.implements(IScheduledTask)

    STATE_CONNECTING = 'CONNECTING'
    STATE_FETCH_MISC_CONFIG = 'FETCHING_MISC_CONFIG'
    STATE_FETCH_DEVICE_CONFIG = 'FETCHING_DEVICE_CONFIG'
    STATE_PROCESS_DEVICE_CONFIG = 'PROCESSING_DEVICE_CONFIG'

    _frameworkFactoryName = "core"

    def __init__(self,
                 name,
                 configId=None,
                 scheduleIntervalSeconds=None,
                 taskConfig=None):
        super(ConfigurationLoaderTask, self).__init__()

        # Needed for interface
        self.name = name
        self.configId = configId if configId else name
        self.state = TaskStates.STATE_IDLE

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)

        if taskConfig is None:
            raise TypeError("taskConfig cannot be None")
        self._prefs = taskConfig
        self.interval = self._prefs.configCycleInterval * 60
        self.options = self._prefs.options

        self._daemon = zope.component.getUtility(ICollector)
        self._daemon.heartbeatTimeout = self._prefs.cycleInterval * 3
        log.debug("Heartbeat timeout set to %ds", self._daemon.heartbeatTimeout)

        frameworkFactory = zope.component.queryUtility(IFrameworkFactory, self._frameworkFactoryName)
        self._configProxy = frameworkFactory.getConfigurationProxy()

        self.devices = []
        self.startDelay=0

    def doTask(self):
        """
        Contact zenhub and gather configuration data.

        @return: A task to gather configs
        @rtype: Twisted deferred object
        """
        log.debug("%s gathering configuration", self.name)
        self.startTime = time.time()

        # Were we given a command-line option to collect a single device?
        if self.options.device:
            self.devices = [self.options.device]

        d = self._baseConfigs()
        self._deviceConfigs(d, self.devices)
        d.addCallback(self._notifyConfigLoaded)
        d.addErrback(self._handleError)
        return d

    def _baseConfigs(self):
        """
        Load the configuration that doesn't depend on loading devices.
        """
        d = defer.maybeDeferred(self._configProxy.getPropertyItems,
                                self._prefs)
        d.addCallback(self._processPropertyItems)
        d.addCallback(self._processThresholdClasses)
        d.addCallback(self._processThresholds)
        return d

    def _deviceConfigs(self, d, devices):
        """
        Load the device configuration
        """
        d.addCallback(self._fetchConfig, devices)
        d.addCallback(self._processConfig)

    def _notifyConfigLoaded(self, result):
        self._daemon.runPostConfigTasks()
        return defer.succeed("Configuration loaded")

    def _handleError(self, result):
        if isinstance(result, Failure):
            log.error("Task %s configure failed: %s",
                      self.name, result.getErrorMessage())

            # stop if a single device was requested and nothing found
            if self.options.device or not self.options.cycle:
                self._daemon.stop()

            ex = result.value
            if isinstance(ex, HubDown):
                result = str(ex)
                # Allow the loader to be reaped and re-added
                self.state = TaskStates.STATE_COMPLETED
        return result

    def _processThresholds(self, thresholds):
        rrdCreateCommand = '\n'.join(self._prefs.defaultRRDCreateCommand)
        self._daemon._configureRRD(rrdCreateCommand, thresholds)

    def _processThresholdClasses(self, thresholdClasses):
        self._daemon._loadThresholdClasses(thresholdClasses)

        d = defer.maybeDeferred(self._configProxy.getThresholds,
                                self._prefs)
        return d

    def _processPropertyItems(self, propertyItems):
        self.state = self.STATE_FETCH_MISC_CONFIG
        self._daemon._setCollectorPreferences(propertyItems)

        d = defer.maybeDeferred(self._configProxy.getThresholdClasses,
                                self._prefs)
        return d

    def _fetchConfig(self, result, devices):
        self.state = self.STATE_FETCH_DEVICE_CONFIG
        return defer.maybeDeferred(self._configProxy.getConfigProxies,
                                   self._prefs, devices)

    @defer.inlineCallbacks
    def _processConfig(self, configs, purgeOmitted=True):
        if self.options.device:
            configs = [cfg for cfg in configs \
                            if self.options.device in (cfg.id, cfg.configId)]
            if not configs:
                log.error("Configuration for %s unavailable -- " \
                               "is that the correct name?",
                               self.options.device)

        if not configs:
            # No devices (eg new install), -d name doesn't exist or
            # device explicitly ignored by zenhub service.
            if not self.options.cycle:
                self._daemon.stop()
            defer.returnValue(['No device configuration to load'])

        self.state = self.STATE_PROCESS_DEVICE_CONFIG
        yield self._daemon._updateDeviceConfigs(configs, purgeOmitted)
        defer.returnValue(configs)

    def cleanup(self):
        pass # Required by interface
