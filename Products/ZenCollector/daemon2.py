import argparse
import logging
import signal

from metrology import Metrology
from metrology.instruments import Gauge
from twisted.application.internet import ClientService, backoffPolicy
from twisted.cred.credentials import UsernamePassword
from twisted.internet import defer, reactor, task
from twisted.internet.endpoints import clientFromString
from twisted.spread import pb

# from twisted.python.failure import Failure
from zope.component import (
    createObject,
    # getUtilitiesFor,
    provideUtility,
    queryUtility,
)
from zope.interface import implementer

from Products.ZenHub.server import ZenPBClientFactory
from Products.ZenHub.metricpublisher import publisher
from Products.ZenUtils.observable import ObservableProxy
from Products.ZenUtils.config import ConfigLoader
from Products.ZenUtils.PBUtil import setKeepAlive
from Products.ZenUtils.Utils import zenPath

from Products.ZenCollector.interfaces import (
    ICollector,
    ICollectorPreferences,
    # IConfigurationDispatchingFilter,
    IConfigurationListener,
    IDataService,
    IEventService,
    IFrameworkFactory,
    ITaskSplitter,
)
from Products.ZenCollector.listeners import (
    DummyListener,
    ConfigListenerNotifier,
    DeviceGuidListener,
)

# from Products.ZenCollector.utils.maintenance import MaintenanceCycle

log = logging.getLogger("zen.daemon")

DUMMY_LISTENER = DummyListener()
CONFIG_LOADER_NAME = "configLoader"


def getLogger(obj):
    """Return a logger based on the name of the given class."""
    return log.getChild(type(obj).__name__.lower())


@implementer(ICollector, IDataService, IEventService)
class CollectionDaemon(pb.Referenceable):
    """ """

    _frameworkFactoryName = ""
    """
    Identifies the IFrameworkFactory implementation to use.

    :type: str
    """

    initialServices = ["EventService"]
    """
    Initial set of ZenHub services to request.

    :type: Sequence[str]
    """

    metricExtraTags = True
    """
    Subclasses can use this to check for metric tag support without
    inspection.  Defaults to True.

    :type: boolean
    """

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
        if not IConfigurationListener.providedBy(configurationListener):
            raise TypeError(
                "configurationListener must provide IConfigurationListener"
            )

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

        self.options = _getConfigOptions()

        self._prefs = ObservableProxy(preferences)
        self._prefs.attachAttributeObserver(
            "configCycleInterval", self._rescheduleConfig
        )
        self._taskSplitter = taskSplitter
        self._configListener = ConfigListenerNotifier()
        self._configListener.addListener(configurationListener)
        self._configListener.addListener(DeviceGuidListener(self))
        self._initializationCallback = initializationCallback
        self._stoppingCallback = stoppingCallback

        self.name = self.preferences.collectorName
        self._statService = createObject("statistics-service")
        # provideUtility(self._statService, IStatisticsService)

        if self.options.cycle:
            # setup daemon statistics (deprecated names)
            self._statService.addStatistic("devices", "GAUGE")
            self._statService.addStatistic("dataPoints", "DERIVE")
            self._statService.addStatistic("runningTasks", "GAUGE")
            self._statService.addStatistic("taskCount", "GAUGE")
            self._statService.addStatistic("queuedTasks", "GAUGE")
            self._statService.addStatistic("missedRuns", "GAUGE")

            # Namespace these a bit so they can be used in ZP monitoring.
            # Prefer these stat names and metrology in future refs
            self._dataPointsMetric = Metrology.meter(
                "collectordaemon.dataPoints"
            )
            daemon = self

            class DeviceGauge(Gauge):
                @property
                def value(self):
                    return len(daemon._devices)

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

        self._deviceGuids = {}
        self._devices = set()
        self._unresponsiveDevices = set()
        self._rrd = None
        self._metric_writer = None
        self._derivative_tracker = None
        self.reconfigureTimeout = None

        # Keep track of pending tasks if we're doing a single run, and not a
        # continuous cycle
        if not self.options.cycle:
            self._completedTasks = 0
            self._pendingTasks = []

        frameworkFactory = queryUtility(
            IFrameworkFactory, self._frameworkFactoryName
        )
        self._configProxy = frameworkFactory.getConfigurationProxy()
        self._scheduler = frameworkFactory.getScheduler()
        self._scheduler.maxTasks = self.options.maxTasks
        self._ConfigurationLoaderTask = (
            frameworkFactory.getConfigurationLoaderTask()
        )

        # Update initialServices to include the configuration service.
        self.initialServices += [self.preferences.configurationService]

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

        # Configure/initialize the ZenHub client
        creds = UsernamePassword(
            self.options.hubusername, self.options.hubpassword
        )
        endpointDescriptor = "tcp:{host}:{port}".format(
            host=self.options.hubhost, port=self.options.hubport
        )
        endpoint = clientFromString(reactor, endpointDescriptor)
        self.__client = ZenHubClient(
            reactor,
            endpoint,
            creds,
            self.options.hub_response_timeout,
            self._main,
        )

    @property
    def preferences(self):
        """
        The preferences object of this daemon.

        :rtype: ICollectorPreferences
        """
        return self._prefs

    def start(self):
        """Start collection daemon processing."""
        # self.log.debug("establishing SIGUSR1 signal handler")
        # signal.signal(signal.SIGUSR1, self.sighandler_USR1)
        # self.log.debug("establishing SIGUSR2 signal handler")
        # signal.signal(signal.SIGUSR2, self.sighandler_USR2)

        self.__client.start()

        # reactor.addSystemEventTrigger("after", "startup", self._main)

        self.__reactor.addSystemEventTrigger(
            "before", "shutdown", self.__client.stop
        )

        # self._metric_manager.start()
        # self.__reactor.addSystemEventTrigger(
        #     "before", "shutdown", self._metric_manager.stop
        # )

        # self.__reactor.addSystemEventTrigger(
        #     "after", "shutdown", self.reportStats
        # )

    def run(self):
        self.start()
        reactor.run()

    @defer.inlineCallbacks
    def _main(self, zenhub):
        self.__zenhub = zenhub
        try:
            self.__zenhubId = yield zenhub.callRemote("getHubInstanceId")

            self.log.debug(
                "Setting up initial services: %s",
                ", ".join(self.initialServices),
            )
            for name in self.initialServices:
                try:
                    service = yield zenhub.callRemote(
                        "getService", name, self, self.options.__dict__
                    )
                    self.services[name] = service
                    self.log.info("retrieved service  service=%s", name)
                    # service.notifyOnDisconnect(???)
                except Exception as ex:
                    self.log.error(
                        "failed to retrieve service  service=%s error=%s",
                        name,
                        ex,
                    )

            if self._initializationCallback is not None:
                yield defer.maybeDeferred(self._initializationCallback())

            yield self._initEncryptionKey()
            # yield self._startConfigCycle()
            # yield self._startMaintenance()
        except Exception as ex:
            self.log.critical("Unrecoverable Error: %s", ex)
            self.log.exception("Unrecoverable Error: %s")
            # stopping callbacks later
            reactor.stop()

    @defer.inlineCallbacks
    def _initEncryptionKey(self, prv_cb_result=None):
        # Encrypt dummy msg in order to initialize the encryption key.
        # The 'yield' does not return until the key is initialized.
        data = yield self._configProxy.encrypt("Hello")
        if data:  # Encrypt returns None if an exception is raised
            self.encryptionKeyInitialized = True
            self.log.info("Daemon's encryption key initialized")

    @defer.inlineCallbacks
    def _startConfigCycle(self, result=None, startDelay=0):
        configLoader = self._ConfigurationLoaderTask(
            CONFIG_LOADER_NAME, taskConfig=self.preferences
        )
        configLoader.startDelay = startDelay
        # Don't add the config loader task if the scheduler already has
        # an instance of it.
        if configLoader not in self._scheduler:
            self._scheduler.addTask(configLoader)
        else:
            self.log.info("%s already added to scheduler", configLoader.name)
        return defer.succeed("Configuration loader task started")

    # @defer.inlineCallbacks
    # def _startMaintenance(self, ignored=None):
    #     if not self.options.cycle:
    #         return
    #     if self.options.logTaskStats > 0:
    #         log.debug("Starting Task Stat logging")
    #         loop = task.LoopingCall(self._displayStatistics, verbose=True)
    #         loop.start(self.options.logTaskStats, now=False)

    #     interval = self.preferences.cycleInterval
    #     self.log.debug("Initializing maintenance Cycle")
    #     maintenanceCycle = MaintenanceCycle(
    #         interval, None, self._maintenanceCycle
    #     )
    #     maintenanceCycle.start()

    # @defer.inlineCallbacks
    # def _maintenanceCycle(self, ignored=None):
    #     """
    #     Perform daemon maintenance processing on a periodic schedule.

    #     Initially called after the daemon configuration loader task is added,
    #     but afterward will self-schedule each run.
    #     """
    #     try:
    #         self.log.debug("Performing periodic maintenance")
    #         if not self.options.cycle:
    #             ret = "No maintenance required"
    #         elif getattr(self.preferences, "pauseUnreachableDevices", True):
    #             # TODO: handle different types of device issues
    #             ret = yield self._pauseUnreachableDevices()
    #         else:
    #             ret = None
    #         defer.returnValue(ret)
    #     except Exception:
    #         self.log.exception("failure in _maintenanceCycle")
    #         raise


def _getArgsFromConfigFile(filename):
    files = []
    try:
        files = [
            open(zenPath("etc", "global.conf"), "r"),
            open(zenPath("etc", filename), "r"),
        ]
        config = ConfigLoader(files)()
        args = []
        for k, v in config.items():
            if v:
                args.extend(["--%s" % (k,), v])
        return args
    finally:
        for f in files:
            f.close()


def _getConfigOptions():
    import sys

    args = sys.argv[1:]
    conf = _getArgsFromConfigFile("zenperfsnmp.conf")
    if conf:
        args = conf + args
    parser = _getArgParser()
    options, _ = parser.parse_known_args(args=args)
    return options


def loglevel(val):
    level = logging._levelNames.get(val)
    if level is None:
        level = int(val)
        if level not in logging._levelNames:
            raise ValueError("unknown log level: %s" % (level,))
    return level


def addLoggingArgs(parser):
    group = parser.add_argument_group(title="Logging Options")
    group.add_argument(
        "-v",
        "--logseverity",
        dest="logseverity",
        default=logging.INFO,
        type=loglevel,
        choices=tuple(logging._levelNames.keys()),
        help="Logging severity threshold",
    )
    group.add_argument(
        "--logpath",
        dest="logpath",
        default=zenPath("log"),
        type=str,
        help="Specify the directory to write the log file",
    )
    group.add_argument(
        "--maxlogsize",
        dest="maxLogKiloBytes",
        default=10240,
        type=int,
        help="Max size of log file in kilobytes",
    )
    group.add_argument(
        "--maxbackuplogs",
        dest="maxBackupLogs",
        default=3,
        type=int,
        help="Maximum number of log files",
    )
    exclusive = group.add_mutually_exclusive_group()
    exclusive.add_argument(
        "--duallog",
        default=False,
        dest="duallog",
        action="store_true",
        help="Log to console and log file",
    )
    exclusive.add_argument(
        "--logfileonly",
        default=False,
        dest="logfileonly",
        action="store_true",
        help="Log to log file and not console",
    )


PB_PORT = 8789
DEFAULT_HUB_HOST = "localhost"
DEFAULT_HUB_PORT = PB_PORT
DEFAULT_HUB_USERNAME = "admin"
DEFAULT_HUB_PASSWORD = "zenoss"
DEFAULT_HUB_MONITOR = "localhost"


def addHubArgs(parser):
    group = parser.add_argument_group(title="ZenHub Options")
    group.add_argument(
        "--hubhost", default=DEFAULT_HUB_HOST, help="Host of ZenHub daemon"
    )
    group.add_argument(
        "--hubport",
        type=int,
        default=DEFAULT_HUB_PORT,
        help="Port ZenHub listens on",
    )
    group.add_argument(
        "--hubusername",
        default=DEFAULT_HUB_USERNAME,
        help="Username for ZenHub login",
    )
    group.add_argument(
        "--hubpassword",
        default=DEFAULT_HUB_PASSWORD,
        help="Password for ZenHub login.",
    )
    group.add_argument(
        "--monitor",
        default=DEFAULT_HUB_MONITOR,
        help="Name of monitor instance to use for configuration",
    )
    group.add_argument(
        "--initialHubTimeout",
        type=int,
        default=30,
        help="Initial time to wait for a ZenHub connection",
    )
    group.add_argument(
        "--zenhubpinginterval",
        dest="zhPingInterval",
        default=120,
        type=int,
        help="How often to ping ZenHub",
    )
    group.add_argument(
        "--disable-ping-perspective",
        dest="pingPerspective",
        default=True,
        action="store_false",
        help="Disable ping perspective",
    )


def addEventArgs(parser):
    group = parser.add_argument_group(title="Event Handling Options")
    group.add_argument(
        "--allowduplicateclears",
        dest="allowduplicateclears",
        default=False,
        action="store_true",
        help="Send clear events even when the most "
        "recent event was also a clear event.",
    )
    group.add_argument(
        "--duplicateclearinterval",
        dest="duplicateclearinterval",
        default=0,
        type=int,
        help="Send a clear event every DUPLICATECLEARINTEVAL events.",
    )
    group.add_argument(
        "--eventflushseconds",
        dest="eventflushseconds",
        default=5.0,
        type=float,
        help="Seconds between attempts to flush " "events to ZenHub.",
    )
    group.add_argument(
        "--eventflushchunksize",
        dest="eventflushchunksize",
        default=50,
        type=int,
        help="Number of events to send to ZenHub" "at one time",
    )

    group.add_argument(
        "--maxqueuelen",
        dest="maxqueuelen",
        default=5000,
        type=int,
        help="Maximum number of events to queue",
    )

    group.add_argument(
        "--queuehighwatermark",
        dest="queueHighWaterMark",
        default=0.75,
        type=float,
        help="The size, in percent, of the event queue "
        "when event pushback starts",
    )
    group.add_argument(
        "--disable-event-deduplication",
        dest="deduplicate_events",
        default=True,
        action="store_false",
        help="Disable event de-duplication",
    )


def addMetricArgs(parser):
    group = parser.add_argument_group(title="Metric Self Reporting Options")
    group.add_argument(
        "--redis-url",
        dest="redisUrl",
        default="redis://localhost:{}/0".format(publisher.defaultRedisPort),
        help="redis connection string: redis://[hostname]:[port]/[db]",
    )
    group.add_argument(
        "--metricBufferSize",
        dest="metricBufferSize",
        type=int,
        default=publisher.defaultMetricBufferSize,
        help="Number of metrics to buffer if redis goes down",
    )
    group.add_argument(
        "--metricsChannel",
        dest="metricsChannel",
        default=publisher.defaultMetricsChannel,
        help="redis channel to which metrics are published",
    )
    group.add_argument(
        "--maxOutstandingMetrics",
        dest="maxOutstandingMetrics",
        type=int,
        default=publisher.defaultMaxOutstandingMetrics,
        help="Max Number of metrics to allow in redis",
    )
    group.add_argument(
        "--writeStatistics",
        dest="writeStatistics",
        type=int,
        default=30,
        help="How often to write internal statistics value in seconds",
    )


def addWorkerArgs(parser):
    group = parser.add_argument_group(title="Cluster Options")
    group.add_argument(
        "--dispatch", dest="configDispatch", help=argparse.SUPPRESS
    )
    group.add_argument(
        "--workerid", type=int, default=0, help=argparse.SUPPRESS
    )
    group.add_argument(
        "--workers", type=int, default=1, help=argparse.SUPPRESS
    )


def addAmqpArgs(parser):
    group = parser.add_argument_group(title="AMQP Options")
    group.add_argument(
        "--amqpadminport",
        type=int,
        default=55672,
        help="AMQP Administration Port",
    )
    group.add_argument(
        "--amqpadminusessl",
        default=False,
        action="store_true",
        help="Encrypt communication with the administration port",
    )
    group.add_argument(
        "--amqphost",
        default="127.0.0.1",
        help="AMQP Host Location",
    )
    group.add_argument(
        "--amqppassword",
        default="zenoss",
        help="AMQP Password",
    )
    group.add_argument(
        "--amqpport",
        type=int,
        default=5672,
        help="AMQP Server Port",
    )
    group.add_argument("--amqpuser", default="zenoss", help="AMQP User Name")
    group.add_argument(
        "--amqpusessl",
        default=False,
        action="store_true",
        help="Encrypt communication with the user port",
    )
    group.add_argument(
        "--amqpvhost",
        default="/zenoss",
        help="Default Virtual Host",
    )


def addZodbArgs(parser):
    group = parser.add_argument_group(title="ZODB Options")
    group.add_argument(
        "-R",
        "--zodb-dataroot",
        dest="dataroot",
        default="/zport/dmd",
        help="root object for data load (i.e. /zport/dmd)",
    )
    group.add_argument(
        "--zodb-cachesize",
        type=int,
        default=1000,
        help="in memory cachesize default",
    )
    group.add_argument(
        "--zodb-host",
        default="localhost",
        help="hostname of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-port",
        type=int,
        default=3306,
        help="port of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-admin-user",
        default="root",
        help="user of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-user",
        default="zenoss",
        help="user of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-password",
        default="zenoss",
        help="password of the MySQL server for ZODB",
    )
    group.add_argument(
        "--zodb-db",
        default="zodb",
        help="Name of database for MySQL object store",
    )
    group.add_argument(
        "--zodb-socket",
        help="Name of socket file for MySQL server connection "
        "if host is localhost",
    )
    group.add_argument(
        "--zodb-cacheservers",
        help="memcached servers to use for object cache "
        "(eg. 127.0.0.1:11211)",
    )
    group.add_argument(
        "--zodb-cache-max-object-size",
        type=int,
        help="memcached maximum object size in bytes",
    )
    group.add_argument(
        "--zodb-commit-lock-timeout",
        type=int,
        default=30,
        help=(
            "Specify the number of seconds a database connection will "
            "wait to acquire a database 'commit' lock before failing."
        ),
    )


def addArgs(parser):
    parser.add_argument(
        "-C",
        "--configfile",
        default=zenPath("etc", "blah.conf"),
        help="Use an alternate configuration file",
    )
    parser.add_argument(
        "-d", "--device", help="Specify a device ID to monitor"
    )


def _getArgParser():
    parser = argparse.ArgumentParser(
        description="Collection Daemon",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # subparsers = parser.add_subparsers()
    addArgs(parser)
    addHubArgs(parser)
    addEventArgs(parser)
    addMetricArgs(parser)
    addWorkerArgs(parser)
    addLoggingArgs(parser)
    addAmqpArgs(parser)
    addZodbArgs(parser)
    return parser


def main():
    options = _getConfigOptions()
    print(options)


if __name__ == "__main__":
    main()
