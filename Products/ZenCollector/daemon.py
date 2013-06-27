##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, 2010, 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import signal
import time
import logging
import os

import zope.interface

from twisted.internet import defer, reactor, task
from twisted.python.failure import Failure

from Products.ZenCollector.interfaces import ICollector,\
                                             ICollectorPreferences,\
                                             IDataService,\
                                             IEventService,\
                                             IFrameworkFactory,\
                                             ITaskSplitter,\
                                             IConfigurationListener,\
                                             IStatistic,\
                                             IStatisticsService
from Products.ZenCollector.utils.maintenance import MaintenanceCycle
from Products.ZenHub.PBDaemon import PBDaemon, FakeRemote
from zenoss.collector.publisher import publisher
from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenRRD import RRDUtil
from Products.ZenRRD.Thresholds import Thresholds
from Products.ZenUtils.Utils import importClass, unused
from Products.ZenUtils.picklezipper import Zipper
from Products.ZenUtils.observable import ObservableProxy

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

class ConfigListenerNotifier(object):
    zope.interface.implements(IConfigurationListener)

    _listeners = []

    def addListener(self, listener):
        self._listeners.append(listener)

    def deleted(self, configurationId):
        """
        Called when a configuration is deleted from the collector
        """
        for listener in self._listeners:
            listener.deleted(configurationId)

    def added(self, configuration):
        """
        Called when a configuration is added to the collector
        """
        for listener in self._listeners:
            listener.added(configuration)


    def updated(self, newConfiguration):
        """
        Called when a configuration is updated in collector
        """
        for listener in self._listeners:
            listener.updated(newConfiguration)

class DeviceGuidListener(object):
    zope.interface.implements(IConfigurationListener)

    def __init__(self, daemon):
        self._daemon = daemon

    def deleted(self, configurationId):
        """
        Called when a configuration is deleted from the collector
        """
        self._daemon._deviceGuids.pop(configurationId, None)

    def added(self, configuration):
        """
        Called when a configuration is added to the collector
        """
        deviceGuid = getattr(configuration, 'deviceGuid', None)
        if deviceGuid:
            self._daemon._deviceGuids[configuration.id] = deviceGuid


    def updated(self, newConfiguration):
        """
        Called when a configuration is updated in collector
        """
        deviceGuid = getattr(newConfiguration, 'deviceGuid', None)
        if deviceGuid:
            self._daemon._deviceGuids[newConfiguration.id] = deviceGuid

DUMMY_LISTENER = DummyListener()
CONFIG_LOADER_NAME = 'configLoader'

class CollectorDaemon(RRDDaemon):
    """
    The daemon class for the entire ZenCollector framework. This class bridges
    the gap between the older daemon framework and ZenCollector. New collectors
    no longer should extend this class to implement a new collector.
    """
    zope.interface.implements(ICollector,
                              IDataService,
                              IEventService)

    _frameworkFactoryName = ""

    @property
    def preferences(self):
        """
        Preferences for this daemon
        """
        return self._prefs

    def __init__(self, preferences, taskSplitter, 
                 configurationListener=DUMMY_LISTENER,
                 initializationCallback=None,
                 stoppingCallback=None):
        """
        Constructs a new instance of the CollectorDaemon framework. Normally
        only a singleton instance of a CollectorDaemon should exist within a
        process, but this is not enforced.
        
        @param preferences: the collector configuration
        @type preferences: ICollectorPreferences
        @param taskSplitter: the task splitter to use for this collector
        @type taskSplitter: ITaskSplitter
        @param initializationCallback: a callable that will be executed after
                                       connection to the hub but before
                                       retrieving configuration information
        @type initializationCallback: any callable
        @param stoppingCallback: a callable that will be executed first during
                                 the stopping process. Exceptions will be
                                 logged but otherwise ignored.
        @type stoppingCallback: any callable
        """
        # create the configuration first, so we have the collector name
        # available before activating the rest of the Daemon class hierarchy.
        if not ICollectorPreferences.providedBy(preferences):
            raise TypeError("configuration must provide ICollectorPreferences")
        else:
            self._prefs = ObservableProxy(preferences)
            self._prefs.attachAttributeObserver('configCycleInterval', self._rescheduleConfig)

        if not ITaskSplitter.providedBy(taskSplitter):
            raise TypeError("taskSplitter must provide ITaskSplitter")
        else:
            self._taskSplitter = taskSplitter
        
        if not IConfigurationListener.providedBy(configurationListener):
            raise TypeError(
                    "configurationListener must provide IConfigurationListener")
        self._configListener = ConfigListenerNotifier()
        self._configListener.addListener(configurationListener)
        self._configListener.addListener(DeviceGuidListener(self))
        self._initializationCallback = initializationCallback
        self._stoppingCallback = stoppingCallback

        # register the various interfaces we provide the rest of the system so
        # that collector implementors can easily retrieve a reference back here
        # if needed
        zope.component.provideUtility(self, ICollector)
        zope.component.provideUtility(self, IEventService)
        zope.component.provideUtility(self, IDataService)

        # setup daemon statistics
        self._statService = StatisticsService()
        self._statService.addStatistic("devices", "GAUGE")
        self._statService.addStatistic("cyclePoints", "GAUGE")
        self._statService.addStatistic("dataPoints", "DERIVE")
        self._statService.addStatistic("runningTasks", "GAUGE")
        self._statService.addStatistic("queuedTasks", "GAUGE")
        zope.component.provideUtility(self._statService, IStatisticsService)

        # register the collector's own preferences object so it may be easily
        # retrieved by factories, tasks, etc.
        zope.component.provideUtility(self.preferences,
                                      ICollectorPreferences,
                                      self.preferences.collectorName)

        super(CollectorDaemon, self).__init__(name=self.preferences.collectorName)

        self._deviceGuids = {}
        self._devices = set()
        self._thresholds = Thresholds()
        self._unresponsiveDevices = set()
        self._publisher = None
        self._metricsChannel = publisher.defaultMetricsChannel
        self._rrd = None
        self.reconfigureTimeout = None

        # keep track of pending tasks if we're doing a single run, and not a
        # continuous cycle
        if not self.options.cycle:
            self._completedTasks = 0
            self._pendingTasks = []

        frameworkFactory = zope.component.queryUtility(IFrameworkFactory, self._frameworkFactoryName)
        self._configProxy = frameworkFactory.getConfigurationProxy()
        self._scheduler = frameworkFactory.getScheduler()
        self._scheduler.maxTasks = self.options.maxTasks
        self._ConfigurationLoaderTask = frameworkFactory.getConfigurationLoaderTask()

        # OLD - set the initialServices attribute so that the PBDaemon class
        # will load all of the remote services we need.
        self.initialServices = PBDaemon.initialServices +\
            [self.preferences.configurationService]

        # trap SIGUSR2 so that we can display detailed statistics
        signal.signal(signal.SIGUSR2, self._signalHandler)

        # let the configuration do any additional startup it might need
        self.preferences.postStartup()
        self.addedPostStartupTasks = False

    def buildOptions(self):
        """
        Method called by CmdBase.__init__ to build all of the possible 
        command-line options for this collector daemon.
        """
        super(CollectorDaemon, self).buildOptions()

        maxTasks = getattr(self.preferences, 'maxTasks', None)
        defaultMax = maxTasks if maxTasks else 500
        
        self.parser.add_option('--maxparallel',
                                dest='maxTasks',
                                type='int',
                                default=defaultMax,
                                help='Max number of tasks to run at once, default %default')
        self.parser.add_option('--logTaskStats',
                               dest='logTaskStats',
                               type='int',
                               default=0,
                               help='How often to logs statistics of current tasks, value in seconds; very verbose')
        self.parser.add_option('--redis-url', default='redis://localhost:16379/0',
            help='redis connection string: redis://[hostname]:[port]/[db], default: %default')

        frameworkFactory = zope.component.queryUtility(IFrameworkFactory, self._frameworkFactoryName)
        if hasattr(frameworkFactory, 'getFrameworkBuildOptions'):
            # During upgrades we'll be missing this option
            self._frameworkBuildOptions = frameworkFactory.getFrameworkBuildOptions()
            if self._frameworkBuildOptions:
                self._frameworkBuildOptions(self.parser)

        # give the collector configuration a chance to add options, too
        self.preferences.buildOptions(self.parser)

    def parseOptions(self):
        super(CollectorDaemon, self).parseOptions()
        self.preferences.options = self.options

    def connected(self):
        """
        Method called by PBDaemon after a connection to ZenHub is established.
        """
        return self._startup()

    def _getInitializationCallback(self):
        def doNothing():
            pass

        if self._initializationCallback is not None:
            return self._initializationCallback
        else:
            return doNothing

    def connectTimeout(self):
        super(CollectorDaemon, self).connectTimeout()
        return self._startup()

    def _startup(self):
        d = defer.maybeDeferred( self._getInitializationCallback() )
        d.addCallback( self._startConfigCycle )
        d.addCallback( self._startMaintenance )
        d.addErrback( self._errorStop )
        return d

    def watchdogCycleTime(self):
        """
        Return our cycle time (in minutes)

        @return: cycle time
        @rtype: integer
        """
        return self.preferences.cycleInterval * 2

    def getRemoteConfigServiceProxy(self):
        """
        Called to retrieve the remote configuration service proxy object.
        """
        return self.services.get(self.preferences.configurationService,
                                 FakeRemote())

    def generateEvent(self, event, **kw):
        eventCopy = super(CollectorDaemon, self).generateEvent(event, **kw)
        if eventCopy.get("device"):
            device_id = eventCopy.get("device")
            guid = self._deviceGuids.get(device_id)
            if guid:
                eventCopy['device_guid'] = guid
        return eventCopy

    def writeMetric(self, metric, value, timestamp, uuid):
        self._publisher.put(self._metricsChannel, metric, value, timestamp, uuid)

    def writeRRD(self, path, value, rrdType, rrdCommand=None, cycleTime=None,
                 min='U', max='U', threshEventData={}, timestamp='N', allowStaleDatapoint=True):
        now = time.time()

        self.writeMetric(os.path.basename(path), value, now, os.path.dirname(path))

        # hasThresholds = bool(self._thresholds.byFilename.get(path))
        # if hasThresholds:
        #     rrd_write_fn = self._rrd.save
        # else:
        #     rrd_write_fn = self._rrd.put            
        # 
        # # save the raw data directly to the RRD files
        # value = rrd_write_fn(
        #     path,
        #     value,
        #     rrdType,
        #     rrdCommand,
        #     cycleTime,
        #     min,
        #     max,
        #     timestamp=timestamp,
        #     allowStaleDatapoint=allowStaleDatapoint,
        # )

        # # check for threshold breaches and send events when needed
        # if hasThresholds:
        #     if 'eventKey' in threshEventData:
        #         eventKeyPrefix = [threshEventData['eventKey']]
        #     else:
        #         eventKeyPrefix = [path.rsplit('/')[-1]]

        #     for ev in self._thresholds.check(path, now, value):
        #         parts = eventKeyPrefix[:]
        #         if 'eventKey' in ev:
        #             parts.append(ev['eventKey'])
        #         ev['eventKey'] = '|'.join(parts)

        #         # add any additional values for this threshold
        #         # (only update if key is not in event, or if
        #         # the event's value is blank or None)
        #         for key,value in threshEventData.items():
        #             if ev.get(key, None) in ('',None):
        #                 ev[key] = value

        #         self.sendEvent(ev)

    def readRRD(self, path, consolidationFunction, start, end):
        return RRDUtil.read(path, consolidationFunction, start, end)

    def stop(self, ignored=""):
        if self._stoppingCallback is not None:
            try:
                self._stoppingCallback()
            except Exception:
                self.log.exception('Exception while stopping daemon')
        super(CollectorDaemon, self).stop( ignored )

    def remote_deleteDevice(self, devId):
        """
        Called remotely by ZenHub when a device we're monitoring is deleted.
        """
        # guard against parsing updates during a disconnect
        if devId is None:
            return
        self._deleteDevice(devId)

    def remote_deleteDevices(self, deviceIds):
        """
        Called remotely by ZenHub when devices we're monitoring are deleted.
        """
        # guard against parsing updates during a disconnect
        if deviceIds is None:
            return
        for devId in Zipper.load(deviceIds):
            self._deleteDevice(devId)

    def remote_updateDeviceConfig(self, config):
        """
        Called remotely by ZenHub when asynchronous configuration updates occur.
        """
        # guard against parsing updates during a disconnect
        if config is None:
            return
        self.log.debug("Device %s updated", config.configId)
        if not self.options.device or self.options.device in (config.id, config.configId):
            self._updateConfig(config)
            self._configProxy.updateConfigProxy(self.preferences, config)

    def remote_updateDeviceConfigs(self, configs):
        """
        Called remotely by ZenHub when asynchronous configuration updates occur.
        """
        if configs is None:
            return
        for config in Zipper.load(configs):
            self.remote_updateDeviceConfig(config)
            
    def remote_notifyConfigChanged(self):
        """
        Called from zenhub to notify that the entire config should be updated  
        """
        if self.reconfigureTimeout and self.reconfigureTimeout.active():
            # We will run along with the already scheduled task
            self.log.debug("notifyConfigChanged - using existing call")
            return

        self.log.debug("notifyConfigChanged - scheduling call in 30 seconds")
        self.reconfigureTimeout = reactor.callLater(30, self._rebuildConfig)

    def _rebuildConfig(self):
        """
        Delete and re-add the configuration tasks to completely re-build the configuration.
        """
        if self.reconfigureTimeout and not self.reconfigureTimeout.active():
            self.reconfigureTimeout = None
        self._scheduler.removeTasksForConfig(CONFIG_LOADER_NAME)
        self._startConfigCycle()

    def _rescheduleConfig(self, observable, attrName, oldValue, newValue, **kwargs):
        """
        Delete and re-add the configuration tasks to start on new interval.
        """
        if oldValue != newValue:
            self.log.debug("Changing config task interval from %s to %s minutes" % (oldValue, newValue))
            self._scheduler.removeTasksForConfig(CONFIG_LOADER_NAME)
            #values are in minutes, scheduler takes seconds
            self._startConfigCycle(startDelay=newValue*60)


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
        configId = cfg.configId
        self.log.debug("Processing configuration for %s", configId)

        nextExpectedRuns = {}
        if configId in self._devices:
            tasksToRemove = self._scheduler.getTasksForConfig(configId)
            nextExpectedRuns = { taskToRemove.name: self._scheduler.getNextExpectedRun(taskToRemove.name) for taskToRemove in tasksToRemove }
            self._scheduler.removeTasks(task.name for task in tasksToRemove)
            self._configListener.updated(cfg)
        else:
            self._devices.add(configId)
            self._configListener.added(cfg)

        newTasks = self._taskSplitter.splitConfiguration([cfg])
        self.log.debug("Tasks for config %s: %s", configId, newTasks)

        nowTime = time.time()
        for (taskName, task_) in newTasks.iteritems():
            #if not cycling run the task immediately otherwise let the scheduler
            #decide when to run the task
            now = not self.options.cycle
            nextExpectedRun = nextExpectedRuns.get(taskName, None)
            if nextExpectedRun:
                startDelay = nextExpectedRun - nowTime
                if startDelay <= 0:
                    # handle edge case where we are about to run
                    # so run immediately
                    now = True
                    task_.startDelay = 0
                else:
                    task_.startDelay = startDelay
            self._scheduler.addTask(task_, self._taskCompleteCallback, now)

            # TODO: another hack?
            if hasattr(cfg, 'thresholds'):
                self._thresholds.updateForDevice(configId, cfg.thresholds)

            # if we're not running a normal daemon cycle then keep track of the
            # tasks we just added for this device so that we can shutdown once
            # all pending tasks have completed
            if not self.options.cycle:
                self._pendingTasks.append(taskName)

    @defer.inlineCallbacks
    def _updateDeviceConfigs(self, updatedConfigs, purgeOmitted):
        """
        Update the device configurations for the devices managed by this
        collector.
        @param deviceConfigs a list of device configurations
        @type deviceConfigs list of name,value tuples
        """
        self.log.debug("updateDeviceConfigs: updatedConfigs=%s", (map(str, updatedConfigs)))

        for cfg in updatedConfigs:
            self._updateConfig(cfg)
            # yield time to reactor so other things can happen
            yield task.deferLater(reactor, 0, lambda: None)

        if purgeOmitted:
            self._purgeOmittedDevices(cfg.configId for cfg in updatedConfigs)

    def _purgeOmittedDevices(self, updatedDevices):
        """
        Delete all current devices that are omitted from the list of devices being updated.
        @param updatedDevices a collection of device ids
        @type updatedDevices a sequence of strings
        """
        # remove tasks for the deleted devices
        deletedDevices = set(self._devices) - set(updatedDevices)
        self.log.debug("purgeOmittedDevices: deletedConfigs=%s", ','.join(deletedDevices))
        for configId in deletedDevices:
            self._deleteDevice(configId)
            
    def _deleteDevice(self, deviceId):
        self.log.debug("Device %s deleted" % deviceId)

        self._devices.discard(deviceId)
        self._configListener.deleted(deviceId)
        self._configProxy.deleteConfigProxy(self.preferences, deviceId)
        self._scheduler.removeTasksForConfig(deviceId)

    def _errorStop(self, result):
        """
        Twisted callback to receive fatal messages.
        
        @param result: the Twisted failure
        @type result: failure object
        """
        if isinstance(result, Failure):
            msg = result.getErrorMessage()
        else:
            msg = str(result)
        self.log.critical("Unrecoverable Error: %s", msg)
        self.stop()

    def _startConfigCycle(self, result=None, startDelay=0):
        configLoader = self._ConfigurationLoaderTask(CONFIG_LOADER_NAME,
                                               taskConfig=self.preferences)
        configLoader.startDelay = startDelay
        # Don't add the config loader task if the scheduler already has
        # an instance of it.
        if configLoader not in self._scheduler:
            # Run initial maintenance cycle as soon as possible
            # TODO: should we not run maintenance if running in non-cycle mode?
            self._scheduler.addTask(configLoader)
        else:
            self.log.info("%s already added to scheduler", configLoader.name)
        return defer.succeed("Configuration loader task started")


    def setPropertyItems(self, items):
        """
        Override so that preferences are updated
        """
        super(CollectorDaemon, self).setPropertyItems(items)
        self._setCollectorPreferences(dict(items))


    def _setCollectorPreferences(self, preferenceItems):
        for name, value in preferenceItems.iteritems():
            if not hasattr(self.preferences, name):
                # TODO: make a super-low level debug mode?  The following message isn't helpful
                #self.log.debug("Preferences object does not have attribute %s",
                #               name)
                setattr(self.preferences, name, value)
            elif getattr(self.preferences, name) != value:
                self.log.debug("Updated %s preference to %s", name, value)
                setattr(self.preferences, name, value)

    def _loadThresholdClasses(self, thresholdClasses):
        self.log.debug("Loading classes %s", thresholdClasses)
        for c in thresholdClasses:
            try:
                importClass(c)
            except ImportError:
                log.exception("Unable to import class %s", c)

    def _configureRRD(self, rrdCreateCommand, thresholds):
        self._publisher = publisher.RedisListPublisher()
        self._rrd = RRDUtil.RRDUtil(rrdCreateCommand, self.preferences.cycleInterval)
        self.rrdStats.config(self.options.monitor,
                             self.name,
                             thresholds,
                             rrdCreateCommand)

    def _isRRDConfigured(self):
        return (self.rrdStats and self._rrd)

    def _startMaintenance(self, ignored=None):
        unused(ignored)
        if not self.options.cycle:
            self._maintenanceCycle()
            return
        if self.options.logTaskStats > 0:
            log.debug("Starting Task Stat logging")
            loop = task.LoopingCall(self._displayStatistics, verbose=True)
            loop.start(self.options.logTaskStats, now=False)
        interval = self.preferences.cycleInterval
        self.log.debug("Initializing maintenance Cycle")
        maintenanceCycle = MaintenanceCycle(interval, self, self._maintenanceCycle)
        maintenanceCycle.start()

    def _maintenanceCycle(self, ignored=None):
        """
        Perform daemon maintenance processing on a periodic schedule. Initially
        called after the daemon configuration loader task is added, but afterward
        will self-schedule each run.
        """
        self.log.debug("Performing periodic maintenance")
        def _processDeviceIssues(result):
            self.log.debug("deviceIssues=%r", result)
            if result is None:
                return result  # exception or some other problem

            # Device ping issues returns as a tuple of (deviceId, count, total)
            # and we just want the device id
            newUnresponsiveDevices = set(i[0] for i in result)

            clearedDevices = self._unresponsiveDevices.difference(newUnresponsiveDevices)
            for devId in clearedDevices:
                self.log.debug("Resuming tasks for device %s", devId)
                self._scheduler.resumeTasksForConfig(devId)

            self._unresponsiveDevices = newUnresponsiveDevices
            for devId in self._unresponsiveDevices:
                self.log.debug("Pausing tasks for device %s", devId)
                self._scheduler.pauseTasksForConfig(devId)

            return result

        def _getDeviceIssues(result):
            # TODO: handle different types of device issues, such as WMI issues
            d = self.getDevicePingIssues()
            return d

        def _postStatistics():
            self._displayStatistics()

            # update and post statistics if we've been configured to do so
            if self._isRRDConfigured():
                stat = self._statService.getStatistic("devices")
                stat.value = len(self._devices)

                stat = self._statService.getStatistic("cyclePoints")
                stat.value = self._rrd.endCycle()

                stat = self._statService.getStatistic("dataPoints")
                stat.value = self._rrd.dataPoints

                # Scheduler statistics
                stat = self._statService.getStatistic("runningTasks")
                stat.value = self._scheduler._executor.running

                stat = self._statService.getStatistic("queuedTasks")
                stat.value = self._scheduler._executor.queued

                events = self._statService.postStatistics(self.rrdStats,
                                                          self.preferences.cycleInterval)
                self.sendEvents(events)

        def _maintenance():
            if self.options.cycle:
                d = defer.maybeDeferred(_postStatistics)
                if getattr(self.preferences, 'pauseUnreachableDevices', True):
                    d.addCallback(_getDeviceIssues)
                    d.addCallback(_processDeviceIssues)

            else:
                d = defer.succeed("No maintenance required")
            return d

        d = _maintenance()
        return d

    def runPostConfigTasks(self, result=None):
        """
        Add post-startup tasks from the preferences.

        This may be called with the failure code as well.
        """
        if isinstance(result, Failure):
            pass

        elif not self.addedPostStartupTasks:
            postStartupTasks = getattr(self.preferences, 'postStartupTasks',
                                       lambda : [])
            for task in postStartupTasks():
                self._scheduler.addTask(task, now=True)
            self.addedPostStartupTasks = True

    def _displayStatistics(self, verbose=False):
        if self._rrd:
            self.log.info("%d devices processed (%d datapoints)",
                          len(self._devices), self._rrd.dataPoints)
        else:
            self.log.info("%d devices processed (0 datapoints)",
                          len(self._devices))

        self._scheduler.displayStatistics(verbose)

    def _signalHandler(self, signum, frame):
        self._displayStatistics(True)


class Statistic(object):
    zope.interface.implements(IStatistic)

    def __init__(self, name, type):
        self.value = 0
        self.name = name
        self.type = type


class StatisticsService(object):
    zope.interface.implements(IStatisticsService)

    def __init__(self):
        self._stats = {}

    def addStatistic(self, name, type):
        if name in self._stats:
            raise NameError("Statistic %s already exists" % name)

        if type not in ('DERIVE', 'COUNTER', 'GAUGE'):
            raise TypeError("Statistic type %s not supported" % type)

        stat = Statistic(name, type)
        self._stats[name] = stat

    def getStatistic(self, name):
        return self._stats[name]

    def postStatistics(self, rrdStats, interval):
        events = []
        for stat in self._stats.values():
            # figure out which function to use to post this statistical data
            try:
                func = {
                    'COUNTER' : rrdStats.counter,
                    'GAUGE' : rrdStats.gauge,
                    'DERIVE' : rrdStats.derive,
                }[stat.type]
            except KeyError:
                raise TypeError("Statistic type %s not supported" % stat.type)

            events += func(stat.name, interval, stat.value)

            # counter is an ever-increasing value, but otherwise...
            if stat.type != 'COUNTER':
                stat.value = 0

        return events
