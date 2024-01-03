#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, 2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import json
import logging
import signal
import time
import types

from collections import defaultdict
from contextlib import contextmanager
from optparse import SUPPRESS_HELP, OptParseError

from metrology import Metrology
from twisted.application.internet import ClientService, backoffPolicy
from twisted.cred.credentials import UsernamePassword
from twisted.internet import defer, reactor, error, task
from twisted.internet.endpoints import clientFromString, serverFromString
from twisted.spread import pb
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.web._responses import NOT_FOUND, INTERNAL_SERVER_ERROR
from zope.component import getGlobalSiteManager

import Products.ZenHub as ZENHUB_MODULE

from Products.DataCollector.Plugins import loadPlugins
from Products.ZenHub import PB_PORT
from Products.ZenHub.metricmanager import MetricManager, IMetricManager
from Products.ZenHub.server import (
    ServiceLoader,
    ServiceManager,
    ServiceRegistry,
    UnknownServiceError,
    ZenPBClientFactory,
)
from Products.ZenHub.PBDaemon import RemoteBadMonitor
from Products.ZenUtils.debugtools import ContinuousProfiler
from Products.ZenUtils.PBUtil import setKeepAlive
from Products.ZenUtils.Time import isoDateTime
from Products.ZenUtils.Utils import load_config
from Products.ZenUtils.ZCmdBase import ZCmdBase

IDLE = "None/None"


def getLogger(obj):
    """Return a logger based on the name of the given class."""
    if isinstance(obj, types.InstanceType):
        name = obj.__class__.__name__
    else:
        name = type(obj).__name__
    name = "zen.zenhubworker.%s" % (name.lower())
    return logging.getLogger(name)


class ZenHubWorker(ZCmdBase, pb.Referenceable):
    """Execute ZenHub requests."""

    mname = name = "zenhubworker"

    def __init__(self, reactor):
        """Initialize a ZenHubWorker instance."""
        ZCmdBase.__init__(self)
        load_config("hubworker.zcml", ZENHUB_MODULE)
        self.__reactor = reactor

        if self.options.profiling:
            self.profiler = ContinuousProfiler("ZenHubWorker", log=self.log)
            self.profiler.start()
            reactor.addSystemEventTrigger(
                "before",
                "shutdown",
                self.profiler.stop,
            )

        self.current = IDLE
        self.currentStart = 0
        self.numCalls = Metrology.meter("zenhub.workerCalls")

        self.zem = self.dmd.ZenEventManager
        loadPlugins(self.dmd)

        self.__registry = ServiceRegistry()
        loader = ServiceLoader()
        factory = ServiceReferenceFactory(self)
        self.__manager = ServiceManager(self.__registry, loader, factory)

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
            self,
            self.options.hub_response_timeout,
            self.worklistId,
        )

        # bind the server to the localhost interface so only local
        # connections can be established.
        server_endpoint_descriptor = "tcp:{port}:interface=127.0.0.1".format(
            port=self.options.localport
        )
        # alternative using UNIX socket instead:
        # _endpoint_descriptor = "unix:address=/tmp/collector.sock:lockfile=1"
        server_endpoint = serverFromString(reactor, server_endpoint_descriptor)
        self.__server = _LocalServer(reactor, server_endpoint, self)

        # Setup Metric Reporting
        self.log.debug("Creating async MetricReporter")
        self._metric_manager = MetricManager(
            daemon_tags={
                "zenoss_daemon": "zenhub_worker_%s" % self.instanceId,
                "zenoss_monitor": self.options.monitor,
                "internal": True,
            },
        )
        # Make the metric manager available via zope.component.getUtility
        getGlobalSiteManager().registerUtility(
            self._metric_manager,
            IMetricManager,
            name="zenhub_worker_metricmanager",
        )

    def start(self):
        """Start zenhubworker processing."""
        self.log.debug("establishing SIGUSR1 signal handler")
        signal.signal(signal.SIGUSR1, self.sighandler_USR1)
        self.log.debug("establishing SIGUSR2 signal handler")
        signal.signal(signal.SIGUSR2, self.sighandler_USR2)

        self.__client.start()
        self.__reactor.addSystemEventTrigger(
            "before", "shutdown", self.__client.stop
        )

        self.__server.start()
        self.__reactor.addSystemEventTrigger(
            "before", "shutdown", self.__server.stop
        )

        self._metric_manager.start()
        self.__reactor.addSystemEventTrigger(
            "before", "shutdown", self._metric_manager.stop
        )

        self.__reactor.addSystemEventTrigger(
            "after", "shutdown", self.reportStats
        )

    def audit(self, action):
        """Override default audit behavior.

        Zenhubworker restarts frequently, so no need to audit.
        """
        pass

    def parseOptions(self):
        """Parse options for zenhubworker.

        Override parseOptions to capture the worklistId argument.
        """
        super(ZenHubWorker, self).parseOptions()
        if len(self.args) == 0:
            raise OptParseError("ZenHub worklist name not specified")
        self.worklistId = self.args[0]
        self.instanceId = "%s_%s" % (self.worklistId, self.options.workerid)

    def setupLogging(self):
        """Configure logging for zenhubworker.

        Override setupLogging to add instance id/count information to
        all log messages.
        """
        super(ZenHubWorker, self).setupLogging()
        template = (
            "%%(asctime)s %%(levelname)s %%(name)s: (%s) %%(message)s"
        ) % self.instanceId
        rootLog = logging.getLogger()
        formatter = logging.Formatter(template)
        for handler in rootLog.handlers:
            handler.setFormatter(formatter)

    def sighandler_USR1(self, signum, frame):
        """Handle USR1 signals.

        When a USR1 signals is caught and profiling is enabled, the
        zenhubworker's profiler will dump its current statistics before
        calling the base class's sighandler_USR1 method.
        """
        try:
            if self.options.profiling:
                self.profiler.dump_stats()
            super(ZenHubWorker, self).sighandler_USR1(signum, frame)
        except Exception:
            pass

    def sighandler_USR2(self, *args):
        """Handle USR2 signals."""
        try:
            self.reportStats()
        except Exception:
            pass

    def _work_started(self, startTime):
        self.currentStart = startTime
        self.numCalls.mark()

    def _work_finished(self, duration, method):
        self.log.debug("Time in %s: %.2f", method, duration)
        self.current = IDLE
        self.currentStart = 0
        if self.numCalls.count >= self.options.call_limit:
            self.log.info(
                "Call limit of %s reached, "
                "proceeding to shutdown (and restart)",
                self.options.call_limit,
            )
            self.__reactor.callLater(0, self._shutdown)

    def getZenHubStatus(self):
        return "connected" if self.__client.is_connected else "disconnected"

    def getStats(self):
        stats = {"current": self.current}
        if self.current != IDLE:
            stats["current.elapsed"] = time.time() - self.currentStart

        if self.__registry:
            sorted_data = sorted(
                self.__registry.iteritems(),
                key=lambda kv: kv[0][1].rpartition(".")[-1],
            )
            summarized_stats = []
            for (_, svc), svcob in sorted_data:
                svc = "%s" % svc.rpartition(".")[-1]
                for method, stats in sorted(svcob.callStats.items()):
                    summarized_stats.append(
                        {
                            "service": svc,
                            "method": method,
                            "count": stats.numoccurrences,
                            "total": stats.totaltime,
                            "average": stats.totaltime / stats.numoccurrences
                            if stats.numoccurrences
                            else 0.0,
                            "last-run": isoDateTime(stats.lasttime),
                        }
                    )
            stats["statistics"] = summarized_stats

        return stats

    def reportStats(self):
        """Write zenhubworker's current statistics to the log."""
        stats = self.getStats()
        if stats["current"] != IDLE:
            self.log.info(
                "Currently performing %s, elapsed %.2f s",
                stats["current"],
                stats["current.elapsed"],
            )
        else:
            self.log.info("Currently IDLE")
        statistics = stats.get("statistics")
        if statistics:
            loglines = ["Running statistics:"]
            loglines.append(
                " %-50s %-32s %8s %12s %8s %s"
                % (
                    "Service",
                    "Method",
                    "Count",
                    "Total",
                    "Average",
                    "Last Run",
                )
            )
            for entry in statistics:
                loglines.append(
                    " - %-48s %-32s %8d %12.2f %8.2f %s"
                    % (
                        entry["service"],
                        entry["method"],
                        entry["count"],
                        entry["total"],
                        entry["average"],
                        entry["last-run"],
                    ),
                )
            self.log.info("\n".join(loglines))
        else:
            self.log.info("no service activity statistics")

    def remote_reportStatus(self):
        """Write zenhubworker's current statistics to the log.

        This method is the RPC interface to reportStats.
        """
        try:
            self.reportStats()
        except Exception:
            self.log.exception("Failed to report status")

    def remote_getService(self, name, monitor):
        """Return a reference to the named service.

        @param name {str} Name of the service to load
        @param monitor {str} Name of the collection monitor
        """
        try:
            self.syncdb()
            return self.__manager.getService(name, monitor)
        except RemoteBadMonitor:
            # Catch and rethrow this Exception derived exception.
            raise
        except UnknownServiceError:
            self.log.error("Service '%s' not found", name)
            raise
        except Exception as ex:
            self.log.exception("Failed to get service '%s'", name)
            raise pb.Error(str(ex))

    def remote_ping(self):
        """Return "pong".

        Used by ZenHub to determine whether zenhubworker is still active.
        """
        return "pong"

    def _shutdown(self):
        self.log.info("Shutting down")
        try:
            self.__reactor.stop()
        except error.ReactorNotRunning:
            pass

    def buildOptions(self):
        """Add optparse options to the options parser."""
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            "--hubhost",
            dest="hubhost",
            default="localhost",
            help="Host to use for connecting to ZenHub",
        )
        self.parser.add_option(
            "--hubport",
            dest="hubport",
            type="int",
            default=PB_PORT,
            help="Port to use for connecting to ZenHub",
        )
        self.parser.add_option(
            "--hubusername",
            dest="hubusername",
            default="admin",
            help="Login name to use when connecting to ZenHub",
        )
        self.parser.add_option(
            "--hubpassword",
            dest="hubpassword",
            default="zenoss",
            help="password to use when connecting to ZenHub",
        )
        self.parser.add_option(
            "--hub-response-timeout",
            dest="hub_response_timeout",
            default=30,
            type="int",
            help="ZenHub response timeout interval (in seconds) "
            "default: %default",
        )
        self.parser.add_option(
            "--call-limit",
            dest="call_limit",
            type="int",
            default=200,
            help="Maximum number of remote calls before restarting worker",
        )
        self.parser.add_option(
            "--profiling",
            dest="profiling",
            action="store_true",
            default=False,
            help="Run with profiling on",
        )
        self.parser.add_option(
            "--monitor",
            dest="monitor",
            default="localhost",
            help="Name of the performance monitor this hub runs on",
        )
        self.parser.add_option(
            "--workerid",
            dest="workerid",
            type="int",
            default=0,
            help=SUPPRESS_HELP,
        )
        self.parser.add_option(
            "--localport",
            dest="localport",
            type="int",
            default=14682,
            help="The worker responds to /status on this port",
        )


class ZenHubClient(object):
    """A client for connecting to ZenHub as a ZenHub Worker.

    After start is called, this class automatically handles connecting to
    ZenHub, registering the zenhubworker with ZenHub, and automatically
    reconnecting to ZenHub if the connection to ZenHub is corrupted for
    any reason.
    """

    def __init__(
        self,
        reactor,
        endpoint,
        credentials,
        worker,
        timeout,
        worklistId,
    ):
        """Initialize a ZenHubClient instance.

        :type reactor: IReactorCore
        :param endpoint: Where zenhub is found
        :type endpoint: IStreamClientEndpoint
        :param credentials: Credentials to log into ZenHub.
        :type credentials: IUsernamePassword
        :param worker: Reference to worker
        :type worker: IReferenceable
        :param float timeout: Seconds to wait before determining whether
            ZenHub is unresponsive.
        :param str worklistId: Name of the worklist to receive tasks from.
        """
        self.__reactor = reactor
        self.__endpoint = endpoint
        self.__credentials = credentials
        self.__worker = worker
        self.__timeout = timeout
        self.__worklistId = worklistId

        self.__stopping = False
        self.__pinger = None
        self.__service = None

        self.__log = getLogger(self)
        self.__zenhub_connected = False

    @property
    def is_connected(self):
        return self.__zenhub_connected

    def start(self):
        """Start connecting to ZenHub."""
        self.__stopping = False
        factory = ZenPBClientFactory()
        self.__service = ClientService(
            self.__endpoint,
            factory,
            retryPolicy=backoffPolicy(initialDelay=0.5, factor=3.0),
        )
        self.__service.startService()
        self.__prepForConnection()

    def stop(self):
        """Stop connecting to ZenHub."""
        self.__stopping = True
        self.__reset()

    def restart(self):
        """Restart the connect to ZenHub."""
        self.__reset()
        self.start()

    def __reset(self):
        self.__zenhub_connected = False
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        if self.__service:
            self.__service.stopService()
            self.__service = None

    def __prepForConnection(self):
        if not self.__stopping:
            self.__log.info("Prepping for connection")
            self.__service.whenConnected().addCallbacks(
                self.__connected, self.__notConnected
            )

    def __disconnected(self, *args):
        # Called when the connection to ZenHub is lost.
        # Ensures that processing resumes when the connection to ZenHub
        # is restored.
        self.__log.info(
            "Lost connection to ZenHub: %s",
            args[0] if args else "<no reason given>",
        )
        self.__zenhub_connected = False
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        self.__prepForConnection()

    def __notConnected(self, *args):
        self.__log.info("Not connected! %r", args)

    @defer.inlineCallbacks
    def __connected(self, broker):
        # Called when a connection to ZenHub is established.
        # Logs into ZenHub and passes up a worker reference for ZenHub
        # to use to dispatch method calls.

        # Sometimes broker.transport doesn't have a 'socket' attribute
        if not hasattr(broker.transport, "socket"):
            self.restart()
            defer.returnValue(None)

        self.__log.info("Connection to ZenHub established")
        try:
            setKeepAlive(broker.transport.socket)

            zenhub = yield self.__login(broker)
            yield zenhub.callRemote(
                "reportingForWork",
                self.__worker,
                workerId=self.__worker.instanceId,
                worklistId=self.__worklistId,
            )

            ping = PingZenHub(zenhub, self)
            self.__pinger = task.LoopingCall(ping)
            d = self.__pinger.start(self.__timeout, now=False)
            d.addErrback(self.__pingFail)  # Catch and pass on errors
        except defer.CancelledError:
            self.__log.error("Timed out trying to login to ZenHub")
            self.restart()
            defer.returnValue(None)
        except Exception as ex:
            self.__log.error(
                "Unable to report for work: (%s) %s", type(ex).__name__, ex
            )
            self.__zenhub_connected = False
            self.__reactor.stop()
        else:
            self.__log.info("Logged into ZenHub")
            self.__zenhub_connected = True

            # Connection complete; install a listener to be notified if
            # the connection is lost.
            broker.notifyOnDisconnect(self.__disconnected)

    def __login(self, broker):
        d = broker.factory.login(self.__credentials, self.__worker)
        timeoutCall = self.__reactor.callLater(self.__timeout, d.cancel)

        def completedLogin(arg):
            if timeoutCall.active():
                timeoutCall.cancel()
            return arg

        d.addBoth(completedLogin)
        return d

    def __pingFail(self, ex):
        self.__log.error("Pinger failed: %s", ex)


class _ErrorResponse(Resource):
    def __init__(self, code, detail):
        Resource.__init__(self)
        self.code = code
        self.detail = detail

    def render(self, request):
        request.setResponseCode(self.code)
        request.setHeader(b"content-type", b"application/json; charset=utf-8")
        return json.dumps({"error": self.code, "message": self.detail})


class _NotFound(_ErrorResponse):
    def __init__(self):
        _ErrorResponse.__init__(self, NOT_FOUND, "resource not found")


class _ZenResource(Resource):
    def getChild(self, path, request):
        return _NotFound()

    def render(self, request):
        try:
            response = Resource.render(self, request)
            if isinstance(response, Resource):
                return response.render(request)
            return response
        except Exception:
            return _ErrorResponse(
                INTERNAL_SERVER_ERROR, "unexpected problem"
            ).render(request)


class _ZenHubStatus(_ZenResource):
    def __init__(self, worker):
        _ZenResource.__init__(self)
        self._worker = worker

    def render_GET(self, request):
        try:
            request.responseHeaders.addRawHeader(
                b"content-type", b"text/plain; charset=utf-8"
            )
            return self._worker.getZenHubStatus()
        except Exception:
            getLogger(self).exception("failed to get ZenHub connection status")
            return _ErrorResponse(
                INTERNAL_SERVER_ERROR, "zenhub status unavailable"
            )


class _WorkerStats(_ZenResource):
    def __init__(self, worker):
        _ZenResource.__init__(self)
        self._worker = worker

    def render_GET(self, request):
        try:
            request.responseHeaders.addRawHeader(
                b"content-type", b"application/json; charset=utf-8"
            )
            return json.dumps(self._worker.getStats())
        except Exception:
            getLogger(self).exception("failed to get zenhubworker stats")
            return _ErrorResponse(
                INTERNAL_SERVER_ERROR, "zenhubworker statistics unavailable"
            )


class _LocalServer(object):
    """
    Server class to listen to local connections.
    """

    def __init__(self, reactor, endpoint, worker):
        self.__reactor = reactor
        self.__endpoint = endpoint
        self.__worker = worker

        root = _ZenResource()
        root.putChild("zenhub", _ZenHubStatus(self.__worker))
        root.putChild("stats", _WorkerStats(self.__worker))
        self.__site = Site(root)

        self.__listener = None
        self.__log = getLogger(self)

    def start(self):
        """Start listening."""
        d = self.__endpoint.listen(self.__site)
        d.addCallbacks(self._success, self._failure)

    def stop(self):
        if self._listener:
            self._listener.stopListening()

    def _success(self, listener):
        self._listener = listener

    def _failure(self, error):
        self.__log.error(
            "failed to open local port  port=%s error=%r",
            self.__endpoint._port,
            error,
        )
        self.__reactor.stop()


class PingZenHub(object):
    """Simple task to ping ZenHub.

    PingZenHub's real purpose is to allow the ZenHubWorker to detect when
    ZenHub is no longer responsive (for whatever reason).
    """

    def __init__(self, zenhub, client):
        """Initialize a PingZenHub instance."""
        self.__zenhub = zenhub
        self.__client = client
        self.__log = getLogger(self)

    @defer.inlineCallbacks
    def __call__(self):
        """Ping zenhub.

        If the ping fails, causes the connection to ZenHub to reset.
        """
        self.__log.debug("Pinging zenhub")
        try:
            response = yield self.__zenhub.callRemote("ping")
            self.__log.debug("Pinged  zenhub: %s", response)
        except Exception as ex:
            self.__log.error("Ping failed: %s", ex)
            self.__client.restart()


class ServiceReferenceFactory(object):
    """This is a factory that builds ServiceReference objects."""

    def __init__(self, worker):
        """Initialize a ServiceReferenceFactory instance.

        @param worker {ZenHubWorker}
        """
        self.__worker = worker

    def __call__(self, service, name, monitor):
        """Build and return a ServiceReference object.

        @param service {HubService derived} Service object
        @param name {string} Name of the service
        @param monitor {string} Name of the performance monitor (collector)
        """
        return ServiceReference(service, name, monitor, self.__worker)


class ServiceReference(pb.Referenceable):
    """Extends pb.Referenceable for ZenHub service classes."""

    def __init__(self, service, name, monitor, worker):
        """Initialize a ServiceReference instance."""
        self.__name = name
        self.__monitor = monitor
        self.__service = service
        self.__worker = worker
        self.callStats = defaultdict(_CumulativeWorkerStats)
        self.debug = False

    @property
    def name(self):
        """Return the name of the service."""
        return self.__name

    @property
    def monitor(self):
        """Return the name of the collector."""
        return self.__monitor

    @defer.inlineCallbacks
    def remoteMessageReceived(self, broker, message, args, kw):
        """Execute the named method on the service.

        @param broker {pb} Perspective broker
        @param message {str} The method to invoke
        @param args {Tuple[Any]} Positional arguments to pass to method
        @param kw {Dict} Keyword/Value arguments to pass to method
        """
        with self.__update_stats(message):
            # Synchronize local ZODB cache with database
            yield self.__worker.async_syncdb()

            # Execute the request
            result = yield self.__service.remoteMessageReceived(
                broker, message, args, kw
            )

            # Return the result
            defer.returnValue(result)

    @contextmanager
    def __update_stats(self, method):
        try:
            name = self.__name.rpartition(".")[-1]
            self.__worker.current = "%s/%s" % (name, method)
            start = time.time()
            self.__worker._work_started(start)
            yield self.__service
        finally:
            finish = time.time()
            secs = finish - start
            self.callStats[method].addOccurrence(secs, finish)
            self.__service.callTime += secs
            self.__worker._work_finished(secs, method)


class _CumulativeWorkerStats(object):
    """Internal class for maintaining cumulative stats.

    Each instance tracks the number of times and time spent executing
    a specific method.
    """

    def __init__(self):
        self.numoccurrences = 0
        self.totaltime = 0.0
        self.lasttime = 0

    def addOccurrence(self, elapsed, now=None):
        if now is None:
            now = time.time()
        self.numoccurrences += 1
        self.totaltime += elapsed
        self.lasttime = now


if __name__ == "__main__":
    zhw = ZenHubWorker(reactor)
    zhw.start()
    reactor.run()
