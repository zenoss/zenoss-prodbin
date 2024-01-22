##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, 2010, 2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import itertools
import json
import re
import signal
import time

from optparse import SUPPRESS_HELP

from metrology import Metrology
from metrology.instruments import Gauge
from twisted.internet import defer, reactor, task
from zope.component import (
    getUtilitiesFor,
    provideUtility,
    queryUtility,
    getUtility,
)
from zope.interface import implementer

import Products.ZenCollector as ZENCOLLECTOR_MODULE

from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenUtils import metrics
from Products.ZenUtils.deprecated import deprecated
from Products.ZenUtils.observable import ObservableProxy
from Products.ZenUtils.Utils import load_config

from .config import DeviceConfigLoader
from .interfaces import (
    ICollector,
    ICollectorPreferences,
    IConfigurationDispatchingFilter,
    IConfigurationListener,
    IDataService,
    IEventService,
    IFrameworkFactory,
    IStatisticsService,
    ITaskSplitter,
)
from .listeners import ConfigListenerNotifier
from .utils.maintenance import MaintenanceCycle, ZenHubHeartbeatSender

CONFIG_LOADER_NAME = "configLoader"


@implementer(ICollector, IDataService, IEventService)
class CollectorDaemon(RRDDaemon):
    """The daemon class for the entire ZenCollector framework."""

    _frameworkFactoryName = "default"  # type: str
    """Identifies the IFrameworkFactory implementation to use."""

    # CollectorDaemon has an additional service: ConfigCache
    initialServices = RRDDaemon.initialServices + ["ConfigCache"]

    metricExtraTags = True
    """
    Subclasses can use this to check for metric tag support without
    inspection.  Defaults to True.

    :type: boolean
    """

    @property
    def preferences(self):  # type: () -> ICollectorPreferences
        """The preferences object of this daemon."""
        return self._prefs

    @property
    def frameworkFactoryName(self):
        return self._frameworkFactoryName

    def __init__(
        self,
        preferences,
        taskSplitter,
        configurationListener=None,
        initializationCallback=None,
        stoppingCallback=None,
    ):
        """
        Initializes a CollectorDaemon instance.

        :param preferences: the collector configuration
        :type preferences: ICollectorPreferences
        :param taskSplitter: the task splitter to use for this collector
        :type taskSplitter: ITaskSplitter
        :param configurationListener: A listener that can react to
            notifications on configuration changes.
        :type configurationListener: IConfigurationListener
        :param initializationCallback: a callable that will be executed after
            connection to the hub but before retrieving configuration
            information.
        :type initializationCallback: any callable, optional
        :param stoppingCallback: a callable that will be executed first during
            the stopping process. Exceptions will be logged but otherwise
            ignored.
        :type stoppingCallback: any callable, optional
        """
        # Create the configuration first, so we have the collector name
        # available before activating the rest of the Daemon class hierarchy.
        if not ICollectorPreferences.providedBy(preferences):
            raise TypeError("configuration must provide ICollectorPreferences")
        if not ITaskSplitter.providedBy(taskSplitter):
            raise TypeError("taskSplitter must provide ITaskSplitter")
        if configurationListener is not None:
            if not IConfigurationListener.providedBy(configurationListener):
                raise TypeError(
                    "configurationListener must provide IConfigurationListener"
                )

        self._prefs = ObservableProxy(preferences)
        self._prefs.attachAttributeObserver(
            "configCycleInterval", self._rescheduleConfig
        )
        self._taskSplitter = taskSplitter
        self._configListener = ConfigListenerNotifier()
        if configurationListener is not None:
            self._configListener.addListener(configurationListener)
        self._initializationCallback = initializationCallback
        self._stoppingCallback = stoppingCallback

        # Register the various interfaces we provide the rest of the system so
        # that collector implementors can easily retrieve a reference back here
        # if needed
        provideUtility(self, ICollector)
        provideUtility(self, IEventService)
        provideUtility(self, IDataService)

        # Register the collector's own preferences object so it may be easily
        # retrieved by factories, tasks, etc.
        provideUtility(
            self.preferences,
            ICollectorPreferences,
            self.preferences.collectorName,
        )
        # There's only one preferences object, so also register an
        # anonymous ICollectorPreferences utility.
        provideUtility(
            self.preferences,
            ICollectorPreferences,
        )

        super(CollectorDaemon, self).__init__(
            name=self.preferences.collectorName
        )

        load_config("collector.zcml", ZENCOLLECTOR_MODULE)

        configFilter = parseWorkerOptions(self.options.__dict__, self.log)
        if configFilter:
            self.preferences.configFilter = configFilter

        dcui = self.options.device_config_update_interval
        if dcui:
            # Convert minutes to seconds
            self._device_config_update_interval = dcui * 60
        else:
            # This covers the case where the device_config_update_interval
            # value is None, zero, or some other False-like value.
            self._device_config_update_interval = 300

        self._deviceGuids = {}
        self._devices = set()  # deprecated; kept for vSphere ZP compatibility
        self._unresponsiveDevices = set()
        self._rrd = None
        self.reconfigureTimeout = None

        # Keep track of pending tasks if we're doing a single run, and not a
        # continuous cycle
        if not self.options.cycle:
            self._completedTasks = 0
            self._pendingTasks = []

        self._configProxy = None
        self._ConfigurationLoaderTask = None
        framework = _getFramework(self.frameworkFactoryName)
        self._scheduler = framework.getScheduler()
        self._scheduler.maxTasks = self.options.maxTasks

        self._statService = getUtility(IStatisticsService)
        if self.options.cycle:
            _configure_stats_service(self._statService, self)

        # Set the initialServices attribute so that the PBDaemon class
        # will load all of the remote services we need.
        self.initialServices.append(self.preferences.configurationService)

        # Trap SIGUSR2 so that we can display detailed statistics
        signal.signal(signal.SIGUSR2, self._signalHandler)

        # Let the configuration do any additional startup it might need
        self.preferences.postStartup()
        self.addedPostStartupTasks = False

        # Variables used by enterprise collector in resmgr
        #
        # Flag that indicates we have finished loading the configs for the
        # first time after a restart
        self.firstConfigLoadDone = False
        # Flag that indicates the daemon has received the encryption key
        # from zenhub
        self.encryptionKeyInitialized = False
        # Flag that indicates the daemon is loading the cached configs
        self.loadingCachedConfigs = False

        self._deviceloader = None
        self._deviceloadertask = None
        self._deviceloadertaskd = None

    def buildOptions(self):
        super(CollectorDaemon, self).buildOptions()

        maxTasks = getattr(self.preferences, "maxTasks", None)
        defaultMax = maxTasks if maxTasks else 500

        self.parser.add_option(
            "--maxparallel",
            dest="maxTasks",
            type="int",
            default=defaultMax,
            help="Max number of tasks to run at once, default %default",
        )
        self.parser.add_option(
            "--logTaskStats",
            dest="logTaskStats",
            type="int",
            default=0,
            help="How often to logs statistics of current tasks, value in "
            "seconds; very verbose. Value of zero disables logging of "
            "task statistics.",
        )
        addWorkerOptions(self.parser)
        self.parser.add_option(
            "--traceMetricName",
            dest="traceMetricName",
            type="string",
            default=None,
            help="trace metrics whose name matches this regex",
        )
        self.parser.add_option(
            "--traceMetricKey",
            dest="traceMetricKey",
            type="string",
            default=None,
            help="trace metrics whose key value matches this regex",
        )
        self.parser.add_option(
            "--device-config-update-interval",
            type="int",
            default=5,
            help="The interval, in minutes, that device configs are "
            "checked for updates (default %default).",
        )

        framework = _getFramework(self.frameworkFactoryName)
        buildOpts = framework.getFrameworkBuildOptions()
        if buildOpts:
            buildOpts(self.parser)

        # give the collector configuration a chance to add options, too
        self.preferences.buildOptions(self.parser)

    def parseOptions(self):
        """Overrides base class to process configuration options."""
        super(CollectorDaemon, self).parseOptions()
        self.preferences.options = self.options

    # @deprecated
    def getInitialServices(self):
        # Retained for compatibility with ZenPacks fixing CollectorDaemon's old
        # behavior regarding the `initialServices` attribute.  This new
        # CollectorDaemon respects changes made to the `initialServices`
        # attribute by subclasses, so the reason for overriding this method
        # is no longer valid.  However, for this method must continue to exist
        # to avoid AttributeError exceptions.
        return self.initialServices

    def watchdogCycleTime(self):
        """
        Return our cycle time (in minutes)

        :return: cycle time
        :rtype: integer
        """
        return self.preferences.cycleInterval * 2

    @defer.inlineCallbacks
    def connected(self):
        """Invoked after a connection to ZenHub is established."""
        try:
            yield defer.maybeDeferred(self._getInitializationCallback())
            framework = _getFramework(self.frameworkFactoryName)
            self.log.debug("using framework factory %s", type(framework))
            self._configProxy = framework.getConfigurationProxy()
            yield self._initEncryptionKey()
            yield self._startConfigCycle()
            yield self._startMaintenance()
            yield self._startTaskStatsLogging()
            yield self._startDeviceConfigLoader()
        except Exception as ex:
            self.log.critical("unrecoverable error: %s", ex)
            self.log.exception("failed during startup")
            self.stop()

    def _getInitializationCallback(self):
        if self._initializationCallback is not None:
            return self._initializationCallback
        return lambda: None

    @defer.inlineCallbacks
    def _initEncryptionKey(self):
        # Encrypt dummy msg in order to initialize the encryption key.
        # The 'yield' does not return until the key is initialized.
        data = yield self._configProxy.encrypt("Hello")
        if data:  # Encrypt returns None if an exception is raised
            self.encryptionKeyInitialized = True
            self.log.debug("initialized encryption key")

    def _startConfigCycle(self, startDelay=0):
        framework = _getFramework(self.frameworkFactoryName)
        configLoader = framework.getConfigurationLoaderTask()(
            CONFIG_LOADER_NAME, taskConfig=self.preferences
        )
        configLoader.startDelay = startDelay
        # Don't add the config loader task if the scheduler already has
        # an instance of it.
        if configLoader not in self._scheduler:
            # Run initial maintenance cycle as soon as possible
            # TODO: should we not run maintenance if running in
            # non-cycle mode?
            self._scheduler.addTask(configLoader)
            self.log.info("scheduled task  task=%s", configLoader.name)
        else:
            self.log.info("task already scheduled  task=%s", configLoader.name)

    def _startMaintenance(self):
        if not self.options.cycle:
            return
        interval = self.preferences.cycleInterval

        if self.worker_id == 0:
            heartbeatSender = ZenHubHeartbeatSender(
                self.options.monitor,
                self.name,
                self.options.heartbeatTimeout,
                self._eventqueue,
            )
        else:
            heartbeatSender = None
        self._maintenanceCycle = MaintenanceCycle(
            interval, heartbeatSender, self._maintenanceCallback
        )
        self._maintenanceCycle.start()

    def _startTaskStatsLogging(self):
        if not (self.options.cycle and self.options.logTaskStats):
            return
        self._taskstatslogger = task.LoopingCall(
            self._displayStatistics, verbose=True
        )
        self._taskstatsloggerd = self._taskstatslogger.start(
            self.options.logTaskStats, now=False
        )
        self.log.debug(
            "started logging task statistics  interval=%d",
            self.options.logTaskStats,
        )
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._taskstatslogger.stop, "before"
        )

    def _startDeviceConfigLoader(self):
        self.log.info(
            "running the device config loader every %d seconds",
            self._device_config_update_interval,
        )
        self._deviceloader = DeviceConfigLoader(
            self.options,
            self._configProxy,
            self._deviceConfigCallback,
        )
        self._deviceloadertask = task.LoopingCall(self._deviceloader)
        self._deviceloadertaskd = self._deviceloadertask.start(
            self._device_config_update_interval
        )
        reactor.addSystemEventTrigger(
            "before", "shutdown", self._deviceloadertask.stop, "before"
        )

    @defer.inlineCallbacks
    def getRemoteConfigCacheProxy(self):
        """Return the remote configuration cache proxy."""
        proxy = yield self.getService("ConfigCache")
        defer.returnValue(proxy)

    def getRemoteConfigServiceProxy(self):
        """Return the remote configuration service proxy object."""
        return self.getServiceNow(self.preferences.configurationService)

    def generateEvent(self, event, **kw):
        eventCopy = super(CollectorDaemon, self).generateEvent(event, **kw)
        if eventCopy and eventCopy.get("device"):
            device_id = eventCopy.get("device")
            guid = self._deviceGuids.get(device_id)
            if guid:
                eventCopy["device_guid"] = guid
        return eventCopy

    def should_trace_metric(self, metric, contextkey):
        """
        Tracer implementation - use this function to indicate whether a given
        metric/contextkey combination is to be traced.

        :param metric: name of the metric in question
        :type metric: str
        :param contextkey: context key of the metric in question
        :return: boolean indicating whether to trace this metric/key
        """
        tests = []
        if self.options.traceMetricName:
            tests.append((self.options.traceMetricName, metric))
        if self.options.traceMetricKey:
            tests.append((self.options.traceMetricKey, contextkey))
        result = [bool(re.search(exp, subj)) for exp, subj in tests]
        return len(result) > 0 and all(result)

    @defer.inlineCallbacks
    def writeMetric(
        self,
        contextKey,
        metric,
        value,
        metricType,
        contextId,
        timestamp="N",
        min="U",
        max="U",
        threshEventData=None,
        deviceId=None,
        contextUUID=None,
        deviceUUID=None,
        extraTags=None,
    ):
        """
        Writes the metric to the metric publisher.

        :param contextKey: This is who the metric applies to. This is usually
            the return value of rrdPath() for a component or device.
        :param metric: the name of the metric, we expect it to be of the form
            datasource_datapoint.
        :param value: the value of the metric.
        :param metricType: type of the metric (e.g. 'COUNTER', 'GAUGE',
            'DERIVE' etc)
        :param contextId: used for the threshold events, the id of who this
            metric is for.
        :param timestamp: defaults to time.time() if not specified,
            the time the metric occurred.
        :param min: used in the derive the min value for the metric.
        :param max: used in the derive the max value for the metric.
        :param threshEventData: extra data put into threshold events.
        :param deviceId: the id of the device for this metric.
        :return: a deferred that fires when the metric gets published.
        """
        timestamp = int(time.time()) if timestamp == "N" else timestamp
        tags = {"contextUUID": contextUUID, "key": contextKey}
        if self.should_trace_metric(metric, contextKey):
            tags["mtrace"] = "{}".format(int(time.time()))

        metric_name = metric
        if deviceId:
            tags["device"] = deviceId

        # compute (and cache) a rate for COUNTER/DERIVE
        if metricType in {"COUNTER", "DERIVE"}:
            if metricType == "COUNTER" and min == "U":
                # COUNTER implies only positive derivatives are valid.
                min = 0

            dkey = "%s:%s" % (contextUUID, metric)
            value = self.derivativeTracker().derivative(
                dkey, (float(value), timestamp), min, max
            )

        # check for threshold breaches and send events when needed
        if value is not None:
            if extraTags:
                tags.update(extraTags)

            # write the  metric to Redis
            try:
                yield defer.maybeDeferred(
                    self.metricWriter().write_metric,
                    metric_name,
                    value,
                    timestamp,
                    tags,
                )
            except Exception as e:
                self.log.debug("error sending metric %s", e)
            yield defer.maybeDeferred(
                self._threshold_notifier.notify,
                contextUUID,
                contextId,
                metric,
                timestamp,
                value,
                threshEventData,
            )

    def writeMetricWithMetadata(
        self,
        metric,
        value,
        metricType,
        timestamp="N",
        min="U",
        max="U",
        threshEventData=None,
        metadata=None,
        extraTags=None,
    ):
        metadata = metadata or {}
        try:
            key = metadata["contextKey"]
            contextId = metadata["contextId"]
            deviceId = metadata["deviceId"]
            contextUUID = metadata["contextUUID"]
            if metadata:
                metric_name = metrics.ensure_prefix(metadata, metric)
            else:
                metric_name = metric
        except KeyError as e:
            raise Exception("Missing necessary metadata: %s" % e.message)

        return self.writeMetric(
            key,
            metric_name,
            value,
            metricType,
            contextId,
            timestamp=timestamp,
            min=min,
            max=max,
            threshEventData=threshEventData,
            deviceId=deviceId,
            contextUUID=contextUUID,
            deviceUUID=metadata.get("deviceUUID"),
            extraTags=extraTags,
        )

    @deprecated
    def writeRRD(
        self,
        path,
        value,
        rrdType,
        rrdCommand=None,
        cycleTime=None,
        min="U",
        max="U",
        threshEventData={},
        timestamp="N",
        allowStaleDatapoint=True,
    ):
        """Use writeMetric instead."""
        # We rely on the fact that rrdPath now returns more information than
        # just the path
        metricinfo, metric = path.rsplit("/", 1)
        if "METRIC_DATA" not in str(metricinfo):
            raise Exception(
                "Unable to write Metric with given path { %s } "
                "please see the rrdpath method" % (metricinfo,)
            )

        metadata = json.loads(metricinfo)
        # reroute to new writeMetric method
        return self.writeMetricWithMetadata(
            metric,
            value,
            rrdType,
            timestamp,
            min,
            max,
            threshEventData,
            metadata,
        )

    def stop(self, ignored=""):
        if self._stoppingCallback is not None:
            try:
                self._stoppingCallback()
            except Exception:
                self.log.exception("exception while stopping daemon")
        super(CollectorDaemon, self).stop(ignored)

    def _rescheduleConfig(
        self, observable, attrName, oldValue, newValue, **kwargs
    ):
        """
        Delete and re-add the configuration tasks to start on new interval.
        """
        if oldValue != newValue:
            self.log.info(
                "changing config task interval from %s to %s minutes",
                oldValue,
                newValue,
            )
            self._scheduler.removeTasksForConfig(CONFIG_LOADER_NAME)
            # values are in minutes, scheduler takes seconds
            self._startConfigCycle(newValue * 60)

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

    def _deviceConfigCallback(self, new, updated, removed):
        """
        Update the device configs for the devices this collector manages.

        :param deviceConfigs: a list of device configurations
        :type deviceConfigs: list of name,value tuples
        """
        for deviceId in removed:
            self._deleteDevice(deviceId)

        for cfg in itertools.chain(new, updated):
            self._updateConfig(cfg)

        self.log.debug(
            "processed %d new, %d updated, %d removed device configs",
            len(new),
            len(updated),
            len(removed),
        )

    def _deleteDevice(self, deviceId):
        self.log.debug("deleted device  device-id=%s", deviceId)
        self._configListener.deleted(deviceId)
        self._scheduler.removeTasksForConfig(deviceId)
        self._deviceGuids.pop(deviceId, None)
        self._devices.discard(deviceId)

    def _updateConfig(self, cfg):
        """
        Update device configuration.

        Returns True if the configuration was processed, otherwise,
        False is returned.
        """
        # guard against parsing updates during a disconnect
        if cfg is None:
            return False

        configFilter = getattr(self.preferences, "configFilter", _always_ok)
        if not (
            (not self.options.device and configFilter(cfg))
            or self.options.device in (cfg.id, cfg.configId)
        ):
            self.log.info(
                "filtered out device config  config-id=%s", cfg.configId
            )
            return False

        configId = cfg.configId
        self.log.info("processing device config  config-id=%s", configId)

        guid = getattr(cfg, "_device_guid", None)
        if guid is not None:
            self._deviceGuids[configId] = guid

        nextExpectedRuns = {}
        if configId in self._deviceloader.deviceIds:
            tasksToRemove = self._scheduler.getTasksForConfig(configId)
            nextExpectedRuns = {
                taskToRemove.name: self._scheduler.getNextExpectedRun(
                    taskToRemove.name
                )
                for taskToRemove in tasksToRemove
            }
            self._scheduler.removeTasks(task.name for task in tasksToRemove)
            self._configListener.updated(cfg)
        else:
            self._devices.add(configId)
            self._configListener.added(cfg)

        newTasks = self._taskSplitter.splitConfiguration([cfg])
        self.log.debug("tasks for config %s: %s", configId, newTasks)

        nowTime = time.time()
        for (taskName, task_) in newTasks.iteritems():
            # if not cycling run the task immediately otherwise let the
            # scheduler decide when to run the task
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
            try:
                self._scheduler.addTask(task_, self._taskCompleteCallback, now)
            except ValueError:
                self.log.exception("failed to schedule task  task=%r", task_)
                continue

            # TODO: another hack?
            if hasattr(cfg, "thresholds"):
                self.getThresholds().updateForDevice(configId, cfg.thresholds)

            # if we're not running a normal daemon cycle then keep track of the
            # tasks we just added for this device so that we can shutdown once
            # all pending tasks have completed
            if not self.options.cycle:
                self._pendingTasks.append(taskName)

        # put tasks on pause after configuration update to prevent
        # unnecessary collections ZEN-25463
        if configId in self._unresponsiveDevices:
            self.log.debug("pausing tasks for device %s", configId)
            self._scheduler.pauseTasksForConfig(configId)

        return True

    def setPropertyItems(self, items):
        """Override so that preferences are updated."""
        super(CollectorDaemon, self).setPropertyItems(items)
        self._setCollectorPreferences(dict(items))

    def _setCollectorPreferences(self, preferenceItems):
        for name, value in preferenceItems.iteritems():
            if not hasattr(self.preferences, name):
                setattr(self.preferences, name, value)
            elif getattr(self.preferences, name) != value:
                self.log.debug("updated %s preference to %s", name, value)
                setattr(self.preferences, name, value)

    def _configureThresholds(self, thresholds):
        self.getThresholds().updateList(thresholds)

    @defer.inlineCallbacks
    def _maintenanceCallback(self, ignored=None):
        """
        Perform daemon maintenance processing on a periodic schedule.

        Initially called after the daemon configuration loader task is added,
        but afterward will self-schedule each run.
        """
        try:
            if self.options.cycle and getattr(
                self.preferences, "pauseUnreachableDevices", True
            ):
                # TODO: handle different types of device issues
                yield self._pauseUnreachableDevices()
        except Exception:
            self.log.exception("failure while running maintenance callback")

    @defer.inlineCallbacks
    def _pauseUnreachableDevices(self):
        issues = yield self.getDevicePingIssues()
        self.log.debug("deviceIssues=%r", issues)
        if issues is None:
            defer.returnValue(issues)  # exception or some other problem

        # Device ping issues returns as a tuple of (deviceId, count, total)
        # and we just want the device id
        newUnresponsiveDevices = set(i[0] for i in issues)

        clearedDevices = self._unresponsiveDevices.difference(
            newUnresponsiveDevices
        )
        for devId in clearedDevices:
            self.log.debug("resuming tasks for device %s", devId)
            self._scheduler.resumeTasksForConfig(devId)

        self._unresponsiveDevices = newUnresponsiveDevices
        for devId in self._unresponsiveDevices:
            self.log.debug("pausing tasks for device %s", devId)
            self._scheduler.pauseTasksForConfig(devId)

        defer.returnValue(issues)

    def runPostConfigTasks(self):
        """
        Add post-startup tasks from the preferences.

        This may be called with the failure code as well.
        """
        if not self.addedPostStartupTasks:
            postStartupTasks = getattr(
                self.preferences, "postStartupTasks", lambda: []
            )
            for task_ in postStartupTasks():
                self._scheduler.addTask(task_, now=True)
            self.addedPostStartupTasks = True

    def postStatisticsImpl(self):
        self._displayStatistics()

        # update and post statistics if we've been configured to do so
        if self.rrdStats:
            stat = self._statService.getStatistic("devices")
            stat.value = len(self._deviceloader.deviceIds)

            # stat = self._statService.getStatistic("cyclePoints")
            # stat.value = self._rrd.endCycle()

            stat = self._statService.getStatistic("dataPoints")
            stat.value = self.metricWriter().dataPoints

            # Scheduler statistics
            stat = self._statService.getStatistic("runningTasks")
            stat.value = self._scheduler._executor.running

            stat = self._statService.getStatistic("taskCount")
            stat.value = self._scheduler.taskCount

            stat = self._statService.getStatistic("queuedTasks")
            stat.value = self._scheduler._executor.queued

            stat = self._statService.getStatistic("missedRuns")
            stat.value = self._scheduler.missedRuns

            diff = (
                self.metricWriter().dataPoints - self._dataPointsMetric.count
            )
            self._dataPointsMetric.mark(diff)

            self._statService.postStatistics(self.rrdStats)

    def _displayStatistics(self, verbose=False):
        if self.metricWriter():
            self.log.debug(
                "%d devices processed (%d samples)",
                len(self._deviceloader.deviceIds),
                self.metricWriter().dataPoints,
            )
        else:
            self.log.debug(
                "%d devices processed (0 samples)",
                len(self._deviceloader.deviceIds),
            )

        self._scheduler.displayStatistics(verbose)

    def _signalHandler(self, signum, frame):
        self._displayStatistics(True)

    @property
    def worker_count(self):
        """The count of service instances."""
        return getattr(self.options, "workers", 1)

    @property
    def worker_id(self):
        """The ID of this particular service instance."""
        return getattr(self.options, "workerid", 0)


def _always_ok(*args):
    return True


def addWorkerOptions(parser):
    parser.add_option(
        "--dispatch", dest="configDispatch", type="string", help=SUPPRESS_HELP
    )
    parser.add_option(
        "--workerid",
        dest="workerid",
        type="int",
        default=0,
        help=SUPPRESS_HELP,
    )
    parser.add_option("--workers", type="int", default=1, help=SUPPRESS_HELP)


def _getFramework(name):
    return queryUtility(IFrameworkFactory, name)


def parseWorkerOptions(options, log):
    dispatchFilterName = options.get("configDispatch", "") if options else ""
    filterFactories = dict(getUtilitiesFor(IConfigurationDispatchingFilter))
    filterFactory = filterFactories.get(
        dispatchFilterName, None
    ) or filterFactories.get("", None)
    if filterFactory:
        filt = filterFactory.getFilter(options)
        log.debug("configured filter: %s:%s", filterFactory, filt)
        return filt


def _configure_stats_service(service, daemon):
    # setup daemon statistics (deprecated names)
    service.addStatistic("devices", "GAUGE")
    service.addStatistic("dataPoints", "DERIVE")
    service.addStatistic("runningTasks", "GAUGE")
    service.addStatistic("taskCount", "GAUGE")
    service.addStatistic("queuedTasks", "GAUGE")
    service.addStatistic("missedRuns", "GAUGE")

    # namespace these a bit so they can be used in ZP monitoring.
    # prefer these stat names and metrology in future refs
    daemon._dataPointsMetric = Metrology.meter("collectordaemon.dataPoints")

    class DeviceGauge(Gauge):
        @property
        def value(self):
            return len(daemon._deviceloader.deviceIds)

    Metrology.gauge("collectordaemon.devices", DeviceGauge())

    # Scheduler statistics
    class RunningTasks(Gauge):
        @property
        def value(self):
            return daemon._scheduler._executor.running

    Metrology.gauge("collectordaemon.runningTasks", RunningTasks())

    class TaskCount(Gauge):
        @property
        def value(self):
            return daemon._scheduler.taskCount

    Metrology.gauge("collectordaemon.taskCount", TaskCount())

    class QueuedTasks(Gauge):
        @property
        def value(self):
            return daemon._scheduler._executor.queued

    Metrology.gauge("collectordaemon.queuedTasks", QueuedTasks())

    class MissedRuns(Gauge):
        @property
        def value(self):
            return daemon._scheduler.missedRuns

    Metrology.gauge("collectordaemon.missedRuns", MissedRuns())
