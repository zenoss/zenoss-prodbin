#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007-2019, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Server that provides access to the Model and Event databases."""

# std lib
import signal
import sys
import logging

# 3rd party
from twisted.internet import reactor, task
from twisted.internet.defer import inlineCallbacks

from zope.component import getUtility, adapts, provideUtility
from zope.event import notify
from zope.interface import implements

# Import Globals before any Zenoss Products
import Globals  # noqa: F401

from Products.ZenUtils.Utils import (
    zenPath, load_config, load_config_override,
)
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenUtils.debugtools import ContinuousProfiler
from Products.ZenEvents.Event import Event, EventHeartbeat
from Products.ZenEvents.ZenEventClasses import App_Start
import Products.ZenMessaging.queuemessaging as QUEUEMESSAGING_MODULE
from Products.ZenMessaging.queuemessaging.interfaces import IEventPublisher

# local
import Products.ZenHub as ZENHUB_MODULE
from Products.ZenHub.interfaces import (
    IHubCreatedEvent,
    IHubWillBeCreatedEvent,
    IHubConfProvider,
    IHubHeartBeatCheck,
    IParserReadyForOptionsEvent,
)
from Products.ZenHub.metricmanager import MetricManager
from Products.ZenHub.invalidationmanager import InvalidationManager
from Products.ZenHub.server import (
    config as server_config,
    getCredentialCheckers,
    IHubServerConfig,
    make_pools,
    make_server_factory,
    make_service_manager,
    start_server,
    stop_server,
    register_legacy_worklist_metrics,
    ReportWorkerStatus,
    StatsMonitor,
    XmlRpcManager,
    ZenHubStatusReporter,
)


def _load_modules():
    # Due to the manipulation of sys.path during the loading of plugins,
    # we can get ObjectMap imported both as DataMaps.ObjectMap and the
    # full-path from Products.  The following gets the class registered
    # with the jelly serialization engine under both names:
    #  1st: get Products.DataCollector.plugins.DataMaps.ObjectMap
    from Products.DataCollector.plugins.DataMaps import ObjectMap  # noqa: F401
    #  2nd: get DataMaps.ObjectMap
    sys.path.insert(0, zenPath('Products', 'DataCollector', 'plugins'))
    import DataMaps  # noqa: F401


_load_modules()

log = logging.getLogger('zen.zenhub')


class ZenHub(ZCmdBase):
    """A server managing access to the Model and Event databases.

    Listen for changes to objects in the Zeo database and update the
    collectors' configuration.

    The remote collectors connect the ZenHub and request configuration
    information and stay connected.  When changes are detected in the
    Zeo database, configuration updates are sent out to collectors
    asynchronously.  In this way, changes made in the web GUI can
    affect collection immediately, instead of waiting for a
    configuration cycle.

    Each collector uses a different, pluggable service within ZenHub
    to translate objects into configuration and data.  ZenPacks can
    add services for their collectors.  Collectors communicate using
    Twisted's Perspective Broker, which provides authenticated,
    asynchronous, bidirectional method invocation.

    ZenHub also provides an XmlRPC interface to some common services
    to support collectors written in other languages.

    ZenHub does very little work in its own process, but instead dispatches
    the work to a pool of zenhubworkers, running zenhubworker.py. zenhub
    manages these workers with 1 data structure:
    - workers - a list of remote PB instances

    TODO: document invalidation workers
    """

    totalTime = 0.
    totalEvents = 0
    totalCallTime = 0.
    mname = name = 'zenhub'

    def __init__(self):
        self.shutdown = False

        super(ZenHub, self).__init__()

        load_config("hub.zcml", ZENHUB_MODULE)
        notify(HubWillBeCreatedEvent(self))

        if self.options.profiling:
            self.profiler = ContinuousProfiler('zenhub', log=self.log)
            self.profiler.start()

        self.zem = self.dmd.ZenEventManager

        # responsible for sending messages to the queues
        load_config_override('twistedpublisher.zcml', QUEUEMESSAGING_MODULE)
        notify(HubCreatedEvent(self))
        self.sendEvent(eventClass=App_Start,
                       summary="%s started" % self.name,
                       severity=0)

        # Initialize ZenHub's RPC servers
        self._monitor = StatsMonitor()
        self._status_reporter = ZenHubStatusReporter(self._monitor)
        self._pools = make_pools()
        self._service_manager = make_service_manager(self._pools)
        authenticators = getCredentialCheckers(self.options.passwordfile)
        self._server_factory = make_server_factory(
            self._pools, self._service_manager, authenticators,
        )
        self._xmlrpc_manager = XmlRpcManager(self.dmd, authenticators[0])
        register_legacy_worklist_metrics()

        # Invalidation Processing
        self._invalidation_manager = InvalidationManager(
            self.dmd,
            self.log,
            self.async_syncdb,
            self.storage.poll_invalidations,
            self.sendEvent,
            poll_interval=self.options.invalidation_poll_interval,
        )

        # Setup Metric Reporting
        self._metric_manager = MetricManager(
            daemon_tags={
                'zenoss_daemon': 'zenhub',
                'zenoss_monitor': self.options.monitor,
                'internal': True,
            })
        provideUtility(self._metric_manager)
        self._metric_writer = self._metric_manager.metric_writer
        self.rrdStats = self._metric_manager.get_rrd_stats(
            self._getConf(), self.zem.sendEvent,
        )

        # set up SIGUSR2 handling
        try:
            signal.signal(signal.SIGUSR2, self.sighandler_USR2)
        except ValueError as ex:
            log.warn("Exception registering USR2 signal handler: %s", ex)
            # If we get called multiple times, this will generate an exception:
            # ValueError: signal only works in main thread
            # Ignore it as we've already set up the signal handler.
            pass
        # ZEN-26671 Wait at least this duration in secs
        # before signaling a worker process
        self.SIGUSR_TIMEOUT = 5

    def main(self):
        """Start the main event loop."""
        if self.options.cycle:
            reactor.callLater(0, self.heartbeat)
            self.log.debug("Creating async MetricReporter")
            self._metric_manager.start()
            reactor.addSystemEventTrigger(
                'before', 'shutdown', self._metric_manager.stop,
            )
            # preserve legacy API
            self.metricreporter = self._metric_manager.metricreporter

        # Start ZenHub services server
        start_server(reactor, self._server_factory)
        reactor.addSystemEventTrigger(
            "before", "shutdown", stop_server,
        )

        # Start XMLRPC server
        self._xmlrpc_manager.start(reactor)

        # Start Processing Invalidations
        self.process_invalidations_task = task.LoopingCall(
            self._invalidation_manager.process_invalidations,
        )
        self.process_invalidations_task.start(
            self.options.invalidation_poll_interval,
        )

        reactor.run()

        self.shutdown = True
        getUtility(IEventPublisher).close()
        if self.options.profiling:
            self.profiler.stop()

    @property
    def counters(self):
        return self._monitor.counters

    def sighandler_USR2(self, signum, frame):
        try:
            self.log.info("\n%s\n", self._status_reporter.getReport())
            notify(ReportWorkerStatus())
        except Exception:
            self.log.exception("Failed to produce report")

    def sighandler_USR1(self, signum, frame):
        if self.options.profiling:
            self.profiler.dump_stats()
        super(ZenHub, self).sighandler_USR1(signum, frame)

    def stop(self):
        self.shutdown = True

    def _getConf(self):
        confProvider = IHubConfProvider(self)
        return confProvider.getHubConf()

    def getService(self, service, monitor):
        return self._service_manager.getService(service, monitor)

    # Legacy API
    def getRRDStats(self):
        return self._metric_manager.get_rrd_stats(
            self._getConf(), self.zem.sendEvent,
        )

    # Legacy API
    @inlineCallbacks
    def processQueue(self):
        """Periodically process database changes."""
        yield self._invalidation_manager.process_invalidations()

    # Legacy API
    def _initialize_invalidation_filters(self):
        self._invalidation_filters = self._invalidation_manager\
            .initialize_invalidation_filters()

    def sendEvent(self, **kw):
        """Post events to the EventManager.

        @type kw: keywords (dict)
        @param kw: the values for an event: device, summary, etc.
        @return: None
        """
        if 'device' not in kw:
            kw['device'] = self.options.monitor
        if 'component' not in kw:
            kw['component'] = self.name
        try:
            self.zem.sendEvent(Event(**kw))
        except Exception:
            self.log.exception("Unable to send an event")

    def heartbeat(self):
        """Send Heartbeat events.

        Also used to update legacy metrics/statistics data.
        """
        seconds = 30
        evt = EventHeartbeat(
            self.options.monitor, self.name, self.options.heartbeatTimeout,
        )
        self.zem.sendEvent(evt)
        self.niceDoggie(seconds)
        reactor.callLater(seconds, self.heartbeat)

        r = self.rrdStats
        r.counter(
            'totalTime', int(self._invalidation_manager.totalTime * 1000),
        )
        r.counter('totalEvents', self._invalidation_manager.totalEvents)
        self._monitor.update_rrd_stats(r, self._service_manager)

        try:
            hbcheck = IHubHeartBeatCheck(self)
            hbcheck.check()
        except Exception:
            self.log.exception("Error processing heartbeat hook")

    def buildOptions(self):
        """Add ZenHub command-line options."""
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            '--xmlrpcport', '-x', dest='xmlrpcport',
            type='int', default=server_config.defaults.xmlrpcport,
            help='Port to use for XML-based Remote Procedure Calls (RPC)')
        self.parser.add_option(
            '--pbport', dest='pbport',
            type='int', default=server_config.defaults.pbport,
            help="Port to use for Twisted's pb service")
        self.parser.add_option(
            '--passwd', dest='passwordfile',
            type='string', default=zenPath('etc', 'hubpasswd'),
            help='File where passwords are stored')
        self.parser.add_option(
            '--monitor', dest='monitor',
            default='localhost',
            help='Name of the distributed monitor this hub runs on')
        self.parser.add_option(
            '--workers-reserved-for-events', dest='workersReservedForEvents',
            type='int', default=1,
            help="Number of worker instances to reserve for handling events")
        self.parser.add_option(
            '--invalidation-poll-interval',
            type='int', default=30,
            help="Interval at which to poll invalidations (default: %default)")
        self.parser.add_option(
            '--profiling', dest='profiling',
            action='store_true', default=False,
            help="Run with profiling on")
        self.parser.add_option(
            '--modeling-pause-timeout',
            type='int', default=server_config.defaults.modeling_pause_timeout,
            help='Maximum number of seconds to pause modeling during ZenPack'
                 ' install/upgrade/removal (default: %default)')

        notify(ParserReadyForOptionsEvent(self.parser))

    def parseOptions(self):
        # Override parseOptions to initialize and install the
        # ServiceManager configuration utility.
        super(ZenHub, self).parseOptions()
        server_config.modeling_pause_timeout = \
            int(self.options.modeling_pause_timeout)
        server_config.xmlrpcport = int(self.options.xmlrpcport)
        server_config.pbport = int(self.options.pbport)
        config_util = server_config.ModuleObjectConfig(server_config)
        provideUtility(config_util, IHubServerConfig)


class DefaultConfProvider(object):  # noqa: D101
    implements(IHubConfProvider)
    adapts(ZenHub)

    def __init__(self, zenhub):
        self._zenhub = zenhub

    def getHubConf(self):
        zenhub = self._zenhub
        return zenhub.dmd.Monitors.Performance._getOb(
            zenhub.options.monitor, None,
        )


class DefaultHubHeartBeatCheck(object):  # noqa: D101
    implements(IHubHeartBeatCheck)
    adapts(ZenHub)

    def __init__(self, zenhub):
        self._zenhub = zenhub

    def check(self):
        pass


class HubWillBeCreatedEvent(object):  # noqa: D101
    implements(IHubWillBeCreatedEvent)

    def __init__(self, hub):
        self.hub = hub


class HubCreatedEvent(object):  # noqa: D101
    implements(IHubCreatedEvent)

    def __init__(self, hub):
        self.hub = hub


class ParserReadyForOptionsEvent(object):  # noqa: D101
    implements(IParserReadyForOptionsEvent)

    def __init__(self, parser):
        self.parser = parser


if __name__ == '__main__':
    from Products.ZenHub.zenhub import ZenHub
    ZenHub().main()
