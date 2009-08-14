###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import sets
import signal
import time

import zope.interface

from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from Products.ZenCollector.interfaces import ICollector,\
                                             ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IOptionService,\
                                             ITaskSplitter
from Products.ZenCollector.scheduler import Scheduler
from Products.ZenHub.PBDaemon import PBDaemon, FakeRemote
from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenRRD.Thresholds import Thresholds
from Products.ZenUtils.Utils import importClass


#
# The default configuration service can be overridden using the --configService
# command-line option. This allows ZenPacks to change the configuration service
# being used without resorting to monkey patching.
#
DEFAULT_CONFIG_SERVICE = 'Products.ZenCollector.config.ConfigurationProxy'


class CollectorDaemon(RRDDaemon):
    """
    The daemon class for the entire ZenCollector framework. This class bridges
    the gap between the older daemon framework and ZenCollector. New collectors
    no longer should extend this class to implement a new collector.
    """
    zope.interface.implements(ICollector,
                              IDataService,
                              IEventService,
                              IOptionService)

    def __init__(self, preferences, taskSplitter):
        """
        Constructs a new instance of the CollectorDaemon framework. Normally
        only a singleton instance of a CollectorDaemon should exist within a
        process, but this is not enforced.
        
        @param preferences: the collector configuration
        @type preferences: ICollectorPreferences
        @param taskSplitter: the task splitter to use for this collector
        @type taskSplitter: ITaskSplitter
        """
        # create the configuration first, so we have the collector name
        # available before activating the rest of the Daemon class hierarchy.
        if not ICollectorPreferences.providedBy(preferences):
            raise TypeError("configuration must provide ICollectorPreferences")
        else:
            self._prefs = preferences

        if not ITaskSplitter.providedBy(taskSplitter):
            raise TypeError("taskSplitter must provide ITaskSplitter")
        else:
            self._taskSplitter = taskSplitter

        # register the various interfaces we provide the rest of the system so
        # that collector implementors can easily retrieve a reference back here
        # if needed
        zope.component.provideUtility(self, ICollector)
        zope.component.provideUtility(self, IEventService)
        zope.component.provideUtility(self, IDataService)
        zope.component.provideUtility(self, IOptionService)

        super(CollectorDaemon, self).__init__(name=self._prefs.collectorName)

        self._devices = sets.Set()
        self._scheduler = Scheduler()
        self._thresholds = Thresholds()
        self._unresponsiveDevices = sets.Set()
        self._rrd = None

        # keep track of pending tasks if we're doing a single run, and not a
        # continuous cycle
        if not self.options.cycle:
            self._completedTasks = 0
            self._pendingTasks = []

        # dynamically create an instance of the object providing the 
        # IConfigurationProxy interface; this easily allows the framework to
        # be extended by a ZenPack without monkey patching.
        configProxyClass = self._getConfigServiceClass()
        self._configProxy = configProxyClass(self._prefs)

        # OLD - set the initialServices attribute so that the PBDaemon class
        # will load all of the remote services we need.
        self.initialServices = PBDaemon.initialServices +\
            [self._prefs.configurationService]

        # trap SIGUSR2 so that we can display detailed statistics
        signal.signal(signal.SIGUSR2, self._signalHandler)

        # let the configuration do any additional startup it might need
        self._prefs.postStartup()

    def buildOptions(self):
        """
        Method called by CmdBase.__init__ to build all of the possible 
        command-line options for this collector daemon.
        """
        super(CollectorDaemon, self).buildOptions()

        self.parser.add_option('--configService',
                               dest='configService',
                               default=DEFAULT_CONFIG_SERVICE,
                               help='Configuration Service class name. '
                               ' Default is %s.' % DEFAULT_CONFIG_SERVICE)

        # give the collector configuration a chance to add options, too
        self._prefs.buildOptions(self.parser)

    def connected(self):
        """
        Method called by PBDaemon after a connection to ZenHub is established.
        """
        def _startMaintenanceCycle(result):
            reactor.callLater(self._prefs.cycleInterval,
                              self._maintenanceCycle)
            return result

        # kick off the initial configuration cycle; once we're configured then
        # we'll begin normal collection activity and the maintenance cycle
        d = self._configCycle()
        d.addCallbacks(_startMaintenanceCycle, self.errorStop)
        return d

    def getRemoteConfigServiceProxy(self):
        """
        Called to retrieve the remote configuration service proxy object.
        """
        return self.services.get(self._prefs.configurationService,
                                 FakeRemote())

    def getCollectorOption(self, optionName):
        return getattr(self.options, optionName, None)

    def setCollectorOption(self, optionName, optionValue):
        setattr(self.options, optionName, optionValue)

    def configureRRD(self, rrdCreateCommand, thresholds):
        """
        Called when this collector daemon should configure its own RRD
        performance statistics.
        """
        self._rrd = RRDUtil(rrdCreateCommand, self._prefs.cycleInterval)
        self.rrdStats.config(self.options.monitor, 
                             self.name, 
                             thresholds,
                             rrdCreateCommand)

    def writeRRD(self, path, value, rrdType, rrdCommand=None, cycleTime=None,
                 min='U', max='U'):
        now = time.time()

        # save the raw data directly to the RRD files
        value = self._rrd.save(path,
                               value,
                               rrdType,
                               rrdCommand,
                               cycleTime,
                               min,
                               max)

        # check for threshold breaches and send events when needed
        for ev in self._thresholds.check(value, now, value):
            ev['eventKey'] = path.rsplit('/')[-1]
            self.sendEvent(ev)

    def remote_deleteDevice(self, devId):
        """
        Called remotely by ZenHub when a device we're monitoring is deleted.
        """
        self.log.debug("Device %s deleted" % devId)

        self._devices.discard(devId)
        self._configProxy.deleteConfig(devId)
        self._scheduler.removeTasksForConfig(devId)

    def remote_updateDeviceConfig(self, config):
        """
        Called remotely by ZenHub when asynchronous configuration updates occur.
        """
        self.log.debug("Device %s updated", config.id)

        if not self.options.device or self.options.device == config.id:
            self._updateConfig(config)
            self._configProxy.updateConfig(config)

    def _taskCompleteCallback(self, taskName):
        # if we're not running a normal daemon cycle then we need to shutdown
        # once all of our pending tasks have completed
        if not self.options.cycle:
            try:
                self._pendingTasks.remove(taskName)
            except ValueError:
                pass

            self._completedTasks += 1

            # if all pending tasks have been completed then shutdown the daemon
            if len(self._pendingTasks) == 0:
                self._displayStatistics()
                self.stop()

    def _updateConfig(self, cfg):
        configId = cfg.id
        self.log.debug("Processing configuration for %s", configId)

        if configId in self._devices:
            self._scheduler.removeTasksForConfig(configId)
        else:
            self._devices.add(configId)

        newTasks = self._taskSplitter.splitConfiguration([cfg])
        self.log.debug("Tasks for config %s: %s", configId, newTasks)

        for (taskName, task) in newTasks.iteritems():
            self._scheduler.addTask(task, self._taskCompleteCallback)

            # TODO: another hack?
            if hasattr(cfg, 'thresholds'):
                self._thresholds.updateForDevice(configId, cfg.thresholds)

            # if we're not running a normal daemon cycle then keep track of the
            # tasks we just added for this device so that we can shutdown once
            # all pending tasks have completed
            if not self.options.cycle:
                self._pendingTasks.append(taskName)

    def _updateDeviceConfigs(self, updatedConfigs):
        """
        Update the device configurations for the devices managed by this
        collector.
        @param deviceConfigs a list of device configurations
        @type deviceConfigs list of name,value tuples
        """
        self.log.debug("updateDeviceConfigs: updatedConfigs=%s", updatedConfigs)

        deleted = self._devices.copy()

        for cfg in updatedConfigs:
            deleted.discard(cfg.id)
            self._updateConfig(cfg)

        # remove tasks for the deleted devices
        for configId in deleted:
            self._scheduler.removeTasksForConfig(configId)

    def _configCycle(self):
        """
        Periodically retrieves collector configuration via the 
        IConfigurationProxy service.
        """
        self.log.debug("_configCycle fetching configuration")

        def _configure():
            devices = []
            # if we were given a command-line option to collect against a single
            # device then make sure configure that information
            if self.options.device:
                devices = [self.options.device]

            return defer.maybeDeferred(self._configProxy.configure, devices)

        def _configureFinished(result):
            if isinstance(result, Failure):
                self.log.error("Configure failed: %s",
                               result.getErrorMessage())

                # stop if a single device was requested and nothing found
                if self.options.device:
                    self.stop()
            else:
                # stop if a single device was requested and its configuration
                # was not found
                if self.options.device and not self.options.cycle:
                    configIds = [cfg.id for cfg in result]
                    if not self.options.device in configIds:
                        self.log.error("Configuration for %s unavailable",
                                       self.options.device)
                        self.stop()

                self.heartbeatTimeout = self._prefs.cycleInterval * 3
                self.log.debug("Heartbeat timeout set to %ds",
                               self.heartbeatTimeout)

                self._updateDeviceConfigs(result)

            # TODO: why is configCycleInterval in minutes but every other
            # interval appears to be in seconds? fix this!
            interval = self._prefs.configCycleInterval * 60
            self.log.debug("Rescheduling configuration check in %d seconds",
                           interval)
            reactor.callLater(interval, self._configCycle)

        d = _configure()
        d.addBoth(_configureFinished)
        return d

    def _maintenanceCycle(self):
        """
        Perform daemon maintenance processing on a periodic schedule. Initially
        called after the daemon is configured, but afterward will self-schedule
        each run.
        """
        self.log.debug("Performing periodic maintenance")

        def _handlePingIssues(result):
            self.log.debug("pingIssues=%r", result)

            # Device ping issues returns as a tuple of (deviceId, count, total)
            # and we just want the device id
            newUnresponsiveDevices = sets.Set([i[0] for i in result])

            clearedDevices = self._unresponsiveDevices.difference(newUnresponsiveDevices)
            for devId in clearedDevices:
                self.log.debug("resuming tasks for device %s", devId)
                self._scheduler.resumeTasksForConfig(devId)

            self._unresponsiveDevices = newUnresponsiveDevices
            for devId in self._unresponsiveDevices:
                self.log.debug("pausing tasks for device %s", devId)
                self._scheduler.pauseTasksForConfig(devId)

            return result

        def _doMaintenance(): # TODO: rename method
            if self.options.cycle:
                self.heartbeat()

                # TODO: are daemon statistics generic or do they need to be 
                # customized?
                if self.rrdStats and self._rrd:
                    self.sendEvents(
                        self.rrdStats.gauge('devices',
                                            self._prefs.cycleInterval,
                                            len(self._devices)) +
                        self.rrdStats.counter('dataPoints',
                                              self._prefs.cycleInterval,
                                              self._rrd.dataPoints)
                        )

                self._displayStatistics()

                d = self.getDevicePingIssues()
                d.addCallback(_handlePingIssues)
                return d
            else:
                return defer.succeed(None)

        def _reschedule(result):
            if isinstance(result, Failure):
                self.log.error("Maintenance failed: %s", result)

            interval = self._prefs.cycleInterval
            if interval > 0:
                self.log.debug("Rescheduling maintenance in %ds", interval)
                reactor.callLater(interval, self._maintenanceCycle)

            return result

        d = _doMaintenance()
        d.addBoth(_reschedule)
        return d

    def _getConfigServiceClass(self):
        # split the entire class path into the module and class name portions
        # so that the module can be imported and then the class loaded
        classParts = self.options.configService.split(".")
        modulePath = ".".join(classParts[:-1])
        className = classParts[-1]
        configServiceClass = importClass(modulePath, className)
        return configServiceClass

    def _displayStatistics(self, verbose=False):
        self.log.info("%d devices processed (%d datapoints)",
              len(self._devices), self._rrd.dataPoints)

        self._scheduler.displayStatistics(verbose)

    def _signalHandler(self, signum, frame):
        self._displayStatistics(True)
