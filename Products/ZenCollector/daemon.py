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
import logging

import zope.interface

from twisted.internet import defer, reactor
from twisted.python.failure import Failure

from Products.ZenCollector.interfaces import ICollector,\
                                             ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IFrameworkFactory,\
                                             ITaskSplitter,\
                                             IConfigurationListener
from Products.ZenHub.PBDaemon import PBDaemon, FakeRemote
from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenRRD.RRDUtil import RRDUtil
from Products.ZenRRD.Thresholds import Thresholds
from Products.ZenUtils.Utils import importClass

log = logging.getLogger("zen.daemon")

class DummyListener(object):
    zope.interface.implements(IConfigurationListener)
    
    def deleted(self, configurationId):
        """
        Called when a configuration is deleted from the collector
        """
        log.debug('DummyListener: configuration %s deleted' % configurationId)

    def added(self, configuration):
        """
        Called when a configuration is added to the collector
        """
        log.debug('DummyListener: configuration %s added' % configuration)


    def updated(self, newConfiguration):
        """
        Called when a configuration is updated in collector
        """
        log.debug('DummyListener: configuration %s updated' % newConfiguration)

DUMMY_LISTENER = DummyListener()

class CollectorDaemon(RRDDaemon):
    """
    The daemon class for the entire ZenCollector framework. This class bridges
    the gap between the older daemon framework and ZenCollector. New collectors
    no longer should extend this class to implement a new collector.
    """
    zope.interface.implements(ICollector,
                              IDataService,
                              IEventService)

    def __init__(self, preferences, taskSplitter, 
                 configurationLister=DUMMY_LISTENER):
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
        
        if not IConfigurationListener.providedBy(configurationLister):
            raise TypeError(
                    "configurationLister must provide IConfigurationListener")
        self._configListener = configurationLister
        
        # register the various interfaces we provide the rest of the system so
        # that collector implementors can easily retrieve a reference back here
        # if needed
        zope.component.provideUtility(self, ICollector)
        zope.component.provideUtility(self, IEventService)
        zope.component.provideUtility(self, IDataService)

        # register the collector's own preferences object so it may be easily
        # retrieved by factories, tasks, etc.
        zope.component.provideUtility(self._prefs,
                                      ICollectorPreferences,
                                      self._prefs.collectorName)

        super(CollectorDaemon, self).__init__(name=self._prefs.collectorName)

        self._devices = sets.Set()
        self._thresholds = Thresholds()
        self._unresponsiveDevices = sets.Set()
        self._rrd = None
        self.reconfigureTimeout = None

        # keep track of pending tasks if we're doing a single run, and not a
        # continuous cycle
        if not self.options.cycle:
            self._completedTasks = 0
            self._pendingTasks = []

        frameworkFactory = zope.component.queryUtility(IFrameworkFactory)
        self._configProxy = frameworkFactory.getConfigurationProxy()
        self._scheduler = frameworkFactory.getScheduler()

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

        # give the collector configuration a chance to add options, too
        self._prefs.buildOptions(self.parser)

    def parseOptions(self):
        super(CollectorDaemon, self).parseOptions()
        self._prefs.options = self.options

    def connected(self):
        """
        Method called by PBDaemon after a connection to ZenHub is established.
        """
        return self._startConfigCycle()

    def connectTimeout(self):
        super(CollectorDaemon, self).connectTimeout()
        return self._startConfigCycle()

    def getRemoteConfigServiceProxy(self):
        """
        Called to retrieve the remote configuration service proxy object.
        """
        return self.services.get(self._prefs.configurationService,
                                 FakeRemote())

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
        for ev in self._thresholds.check(path, now, value):
            ev['eventKey'] = path.rsplit('/')[-1]
            self.sendEvent(ev)

    def remote_deleteDevice(self, devId):
        """
        Called remotely by ZenHub when a device we're monitoring is deleted.
        """
        self._deleteDevice(devId)

    def remote_updateDeviceConfig(self, config):
        """
        Called remotely by ZenHub when asynchronous configuration updates occur.
        """
        self.log.debug("Device %s updated", config.id)

        if not self.options.device or self.options.device == config.id:
            self._updateConfig(config)
            self._configProxy.updateConfigProxy(self._prefs, config)
            
    def remote_notifyConfigChanged(self):
        """
        Called from zenhub to notify that the entire config should be updated  
        """
        self.log.debug('notify config change received')
        if self.reconfigureTimeout and not self.reconfigureTimeout.called:
            self.reconfigureTimeout.cancel()
        self.reconfigureTimeout = reactor.callLater(30, self._configCycle, False)

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
            self._configListener.updated(cfg)
        else:
            self._devices.add(configId)
            self._configListener.added(cfg)

        newTasks = self._taskSplitter.splitConfiguration([cfg])
        self.log.debug("Tasks for config %s: %s", configId, newTasks)

        for (taskName, task) in newTasks.iteritems():
            #if not cycling run the task immediately otherwise let the scheduler
            #decide when to run the task
            now = not self.options.cycle
            self._scheduler.addTask(task, self._taskCompleteCallback, now)

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
            self._deleteDevice(configId)
            
    def _deleteDevice(self, deviceId):
        self.log.debug("Device %s deleted" % deviceId)

        self._devices.discard(deviceId)
        self._configListener.deleted(deviceId)
        self._configProxy.deleteConfigProxy(self._prefs, deviceId)
        self._scheduler.removeTasksForConfig(deviceId)

    def _startConfigCycle(self):
        def _startMaintenanceCycle(result):
            # run initial maintenance cycle as soon as possible
            # TODO: should we not run maintenance if running in non-cycle mode?
            reactor.callLater(0, self._maintenanceCycle)
            return result

        # kick off the initial configuration cycle; once we're configured then
        # we'll begin normal collection activity and the maintenance cycle
        d = self._configCycle()
        d.addCallbacks(_startMaintenanceCycle, self.errorStop)
        return d

    def _setCollectorPreferences(self, preferenceItems):
        for name, value in preferenceItems.iteritems():
            if not hasattr(self._prefs, name):
                self.log.debug("Preferences object does not have attribute %s",
                               name)
                setattr(self._prefs, name, value)
            elif getattr(self._prefs, name) != value:
                self.log.debug("Updated %s preference to %s", name, value)
                setattr(self._prefs, name, value)

    def _loadThresholdClasses(self, thresholdClasses):
        self.log.debug("Loading classes %s", thresholdClasses)
        for c in thresholdClasses:
            try:
                importClass(c)
            except ImportError:
                log.exception("Unable to import class %s", c)

    def _configureRRD(self, rrdCreateCommand, thresholds):
        self._rrd = RRDUtil(rrdCreateCommand, self._prefs.cycleInterval)
        self.rrdStats.config(self.options.monitor,
                             self.name,
                             thresholds,
                             rrdCreateCommand)

    def _configCycle(self, reschedule=True):
        """
        Periodically retrieves collector configuration via the 
        IConfigurationProxy service.
        """
        self.log.debug("_configCycle fetching configuration")

        def _processThresholds(thresholds, devices):
            rrdCreateCommand = '\n'.join(self._prefs.defaultRRDCreateCommand)
            self._configureRRD(rrdCreateCommand, thresholds)

        def _processThresholdClasses(thresholdClasses, devices):
            self._loadThresholdClasses(thresholdClasses)
            
            d = defer.maybeDeferred(self._configProxy.getThresholds,
                                    self._prefs)
            return d

        def _processPropertyItems(propertyItems, devices):
            self._setCollectorPreferences(propertyItems)

            d = defer.maybeDeferred(self._configProxy.getThresholdClasses,
                                    self._prefs)
            return d

        def _fetchConfig(result, devices):
            return defer.maybeDeferred(self._configProxy.getConfigProxies,
                                       self._prefs, devices)

        def _processConfig(result):
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
            return result

        def _reschedule(result):
            # TODO: why is configCycleInterval in minutes but every other
            # interval appears to be in seconds? fix this!
            interval = self._prefs.configCycleInterval * 60
            self.log.debug("Rescheduling configuration check in %d seconds",
                           interval)
            reactor.callLater(interval, self._configCycle)
            return result
        
        def _configure():
            devices = []
            # if we were given a command-line option to collect against a single
            # device then make sure configure that information
            if self.options.device:
                devices = [self.options.device]

            d = defer.maybeDeferred(self._configProxy.getPropertyItems,
                                    self._prefs)
            d.addCallback(_processPropertyItems, devices)
            d.addCallback(_processThresholdClasses, devices)
            d.addCallback(_processThresholds, devices)
            d.addCallback(_fetchConfig, devices)
            d.addCallback(_processConfig)
            return d
        
        def _handleError(result):
            if isinstance(result, Failure):
                self.log.error("Configure failed: %s",
                               result.getErrorMessage())

                # stop if a single device was requested and nothing found
                if self.options.device:
                    self.stop()
            return result
        d = _configure()
        d.addErrback(_handleError)
        if reschedule:
            d.addBoth(_reschedule)
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
                self.log.error("Maintenance failed: %s",
                               result.getErrorMessage())

            interval = self._prefs.cycleInterval
            if interval > 0:
                self.log.debug("Rescheduling maintenance in %ds", interval)
                reactor.callLater(interval, self._maintenanceCycle)

#            return result

        d = _doMaintenance()
        d.addBoth(_reschedule)
        return d

    def _displayStatistics(self, verbose=False):
        self.log.info("%d devices processed (%d datapoints)",
              len(self._devices), self._rrd.dataPoints)

        self._scheduler.displayStatistics(verbose)

    def _signalHandler(self, signum, frame):
        self._displayStatistics(True)
