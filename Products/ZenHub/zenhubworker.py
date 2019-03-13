#! /usr/bin/env python
##############################################################################
#
# Copyright (C) Zenoss, Inc. 2008, 2018 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import os
import signal
import socket
import time

from collections import defaultdict
from contextlib import contextmanager
from optparse import SUPPRESS_HELP

from metrology import Metrology
from twisted.application.internet import ClientService, backoffPolicy
from twisted.cred.credentials import UsernamePassword
from twisted.internet.endpoints import clientFromString
from twisted.internet import defer, reactor, error, task
from twisted.spread import pb
from zope.interface import implementer

import Globals

from Products.DataCollector.plugins import DataMaps
from Products.DataCollector.Plugins import loadPlugins
from Products.ZenHub import PB_PORT, OPTION_STATE, CONNECT_TIMEOUT
from Products.ZenHub.interfaces import IServiceReferenceFactory
from Products.ZenHub.metricmanager import MetricManager
from Products.ZenHub.servicemanager import (
    HubServiceRegistry, UnknownServiceError
)
from Products.ZenHub.PBDaemon import RemoteBadMonitor
from Products.ZenUtils.debugtools import ContinuousProfiler
from Products.ZenUtils.Time import isoDateTime
from Products.ZenUtils.Utils import unused, zenPath, atomicWrite
from Products.ZenUtils.ZCmdBase import ZCmdBase

unused(Globals, DataMaps)

IDLE = "None/None"


def getLogger(obj):
    cls = type(obj)
    name = "zen.zenhubworker.%s" % (cls.__name__)
    return logging.getLogger(name)


def setKeepAlive(sock):
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, OPTION_STATE)
    sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, CONNECT_TIMEOUT)
    interval = max(CONNECT_TIMEOUT / 4, 10)
    sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval)
    sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)


class ZenHubWorker(ZCmdBase, pb.Referenceable):
    """Execute ZenHub requests.
    """

    mname = name = "zenhubworker"

    def __init__(self, reactor):
        ZCmdBase.__init__(self)

        self.__reactor = reactor

        if self.options.profiling:
            self.profiler = ContinuousProfiler('ZenHubWorker', log=self.log)
            self.profiler.start()
            reactor.addSystemEventTrigger(
                'before', 'shutdown', self.profiler.stop
            )

        self.instanceId = self.options.workerid
        self.current = IDLE
        self.currentStart = 0
        self.numCalls = Metrology.meter("zenhub.workerCalls")

        self.zem = self.dmd.ZenEventManager
        loadPlugins(self.dmd)

        serviceFactory = ServiceReferenceFactory(self)
        self.__registry = HubServiceRegistry(self.dmd, serviceFactory)

        # Configure/initialize the ZenHub client
        creds = UsernamePassword(
            self.options.hubusername, self.options.hubpassword
        )
        endpointDescriptor = "tcp:{host}:{port}".format(
            host=self.options.hubhost, port=self.options.hubport
        )
        endpoint = clientFromString(reactor, endpointDescriptor)
        self.__client = ZenHubClient(reactor, endpoint, creds, self, 10.0)

        # Setup Metric Reporting
        self.log.debug("Creating async MetricReporter")
        self._metric_manager = MetricManager(
            daemon_tags={
                'zenoss_daemon': 'zenhub_worker_%s' % self.options.workerid,
                'zenoss_monitor': self.options.monitor,
                'internal': True
            }
        )

    def start(self):
        """
        """
        self.log.debug("establishing SIGUSR1 signal handler")
        signal.signal(signal.SIGUSR1, self.sighandler_USR1)
        self.log.debug("establishing SIGUSR2 signal handler")
        signal.signal(signal.SIGUSR2, self.sighandler_USR2)

        self.__client.start()
        self.__reactor.addSystemEventTrigger(
            'before', 'shutdown', self.__client.stop
        )

        self._metric_manager.start()
        self.__reactor.addSystemEventTrigger(
            'before', 'shutdown', self._metric_manager.stop
        )

        self.__reactor.addSystemEventTrigger(
            "after", "shutdown", self.reportStats
        )

    def audit(self, action):
        """ZenHubWorkers restart all the time, it is not necessary to
        audit log it.
        """
        pass

    def setupLogging(self):
        """Override setupLogging to add instance id/count information to
        all log messages.
        """
        super(ZenHubWorker, self).setupLogging()
        instanceInfo = "(%s)" % (self.options.workerid,)
        template = (
            "%%(asctime)s %%(levelname)s %%(name)s: %s %%(message)s"
        ) % instanceInfo
        rootLog = logging.getLogger()
        formatter = logging.Formatter(template)
        for handler in rootLog.handlers:
            handler.setFormatter(formatter)

    def sighandler_USR1(self, signum, frame):
        try:
            if self.options.profiling:
                self.profiler.dump_stats()
            super(ZenHubWorker, self).sighandler_USR1(signum, frame)
        except Exception:
            pass

    def sighandler_USR2(self, *args):
        try:
            self.reportStats()
        except Exception:
            pass

    def work_started(self, startTime):
        self.currentStart = startTime
        self.numCalls.mark()

    def work_finished(self, duration, method):
        self.log.debug("Time in %s: %.2f", method, duration)
        self.current = IDLE
        self.currentStart = 0
        if self.numCalls.count >= self.options.call_limit:
            self.log.info(
                "Call limit of %s reached, "
                "proceeding to shutdown (and restart)",
                self.options.call_limit
            )
            self.__reactor.callLater(0, self._shutdown)

    def reportStats(self):
        now = time.time()
        if self.current != IDLE:
            self.log.info(
                "Currently performing %s, elapsed %.2f s",
                self.current, now-self.currentStart
            )
        else:
            self.log.info("Currently IDLE")
        if self.__registry:
            loglines = ["Running statistics:"]
            sorted_data = sorted(
                self.__registry.iteritems(),
                key=lambda kvp: (kvp[0][1], kvp[0][0].rpartition('.')[-1])
            )
            for svc, svcob in sorted_data:
                svc = "%s/%s" % (svc[1], svc[0].rpartition('.')[-1])
                for method, stats in sorted(svcob.callStats.items()):
                    loglines.append(
                        " - %-48s %-32s %8d %12.2f %8.2f %s" % (
                            svc, method,
                            stats.numoccurrences,
                            stats.totaltime,
                            stats.totaltime/stats.numoccurrences
                            if stats.numoccurrences else 0.0,
                            isoDateTime(stats.lasttime)
                        )
                    )
            self.log.info('\n'.join(loglines))
        else:
            self.log.info("no service activity statistics")

    def remote_reportStatus(self):
        """Remote command to report the worker's current status to the log.
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
            return self.__registry.getService(name, monitor)
        except RemoteBadMonitor:
            # Catch and rethrow this Exception derived exception.
            raise
        except UnknownServiceError:
            self.log.error("Service '%s' not found", name)
            raise
        except Exception as ex:
            self.log.exception("Failed to get service '%s'", name)
            raise pb.Error(str(ex))

    def _shutdown(self):
        self.log.info("Shutting down")
        try:
            self.__reactor.stop()
        except error.ReactorNotRunning:
            pass

    def buildOptions(self):
        """Options, mostly to find where zenhub lives
        These options should be passed (by file) from zenhub.
        """
        ZCmdBase.buildOptions(self)
        self.parser.add_option(
            '--hubhost', dest='hubhost', default='localhost',
            help="Host to use for connecting to ZenHub"
        )
        self.parser.add_option(
            '--hubport', dest='hubport', type='int', default=PB_PORT,
            help="Port to use for connecting to ZenHub"
        )
        self.parser.add_option(
            '--hubusername', dest='hubusername', default='admin',
            help="Login name to use when connecting to ZenHub"
        )
        self.parser.add_option(
            '--hubpassword', dest='hubpassword', default='zenoss',
            help="password to use when connecting to ZenHub"
        )
        self.parser.add_option(
            '--call-limit', dest='call_limit', type='int', default=200,
            help="Maximum number of remote calls before restarting worker"
        )
        self.parser.add_option(
            '--profiling', dest='profiling',
            action='store_true', default=False, help="Run with profiling on"
        )
        self.parser.add_option(
            '--monitor', dest='monitor', default='localhost',
            help='Name of the performance monitor this hub runs on'
        )
        self.parser.add_option(
            '--workerid', dest='workerid', type='int', default=0,
            help=SUPPRESS_HELP
        )


class ZenHubClient(object):
    """Implements a client for connecting to ZenHub as a ZenHub Worker.
    """

    def __init__(self, reactor, endpoint, credentials, worker, timeout):
        """Initializes a ZenHubClient instance.

        @param reactor {IReactorCore}
        @param endpoint {IStreamClientEndpoint} Where zenhub is found
        @param credentials {IUsernamePassword} Credentials to log into ZenHub.
        @param worker {IReferenceable} Reference to worker
        @param timeout {float} Seconds to wait before determining whether
            ZenHub is unresponsive.
        """
        self.__reactor = reactor
        self.__endpoint = endpoint
        self.__credentials = credentials
        self.__worker = worker
        self.__timeout = timeout

        self.__stopping = False
        self.__pinger = None
        self.__service = None

        self.__log = getLogger(self)
        self.__signalFile = ConnectedToZenHubSignalFile()

    def start(self):
        self.__stopping = False
        factory = pb.PBClientFactory()
        self.__service = ClientService(
            self.__endpoint, factory,
            retryPolicy=backoffPolicy(initialDelay=0.5, factor=3.0)
        )
        self.__service.startService()
        self.__prepForConnection()

    def stop(self):
        self.__stopping = True
        self.__reset()

    def restart(self):
        self.__reset()
        self.start()

    def __reset(self):
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        if self.__service:
            self.__service.stopService()
            self.__service = None
        self.__signalFile.remove()

    def __prepForConnection(self):
        if not self.__stopping:
            self.__log.info("Prepping for connection")
            self.__service.whenConnected().addCallbacks(
                self.__connected, self.__notConnected
            )

    def __disconnected(self, *args):
        """Called when the connection to ZenHub is lost.

        Ensures that processing resumes when the connection to ZenHub
        is restored.
        """
        self.__log.info(
            "Lost connection to ZenHub: %s",
            args[0] if args else "<no reason given>"
        )
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        self.__signalFile.remove()
        self.__prepForConnection()

    def __notConnected(self, *args):
        self.__log.info("Not connected! %r", args)

    @defer.inlineCallbacks
    def __connected(self, broker):
        """Called when a connection to ZenHub is established.

        Logs into ZenHub and passes up a worker reference for ZenHub
        to use to dispatch method calls.
        """
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
                self.__worker, workerId=self.__worker.instanceId
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
                "Unable to report for work: (%s) %s", type(ex), ex
            )
            self.__signalFile.remove()
            self.__reactor.stop()
        else:
            self.__log.info("Logged into ZenHub")
            self.__signalFile.touch()

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


class PingZenHub(object):
    """Simple task to ping ZenHub.

    PingZenHub's real purpose is to allow the ZenHubWorker to detect when
    ZenHub is no longer responsive (for whatever reason).
    """

    def __init__(self, zenhub, client):
        self.__zenhub = zenhub
        self.__client = client
        self.__log = getLogger(self)

    @defer.inlineCallbacks
    def __call__(self):
        self.__log.debug("Pinging zenhub")
        try:
            response = yield self.__zenhub.callRemote("ping")
            self.__log.debug("Pinged  zenhub: %s", response)
        except Exception as ex:
            self.__log.error("Ping failed: %s", ex)
            self.__client.restart()


class ConnectedToZenHubSignalFile(object):

    def __init__(self):
        filename = "zenhub_connected"
        self.__signalFilePath = zenPath('var', filename)
        self.__log = getLogger(self)

    def touch(self):
        atomicWrite(self.__signalFilePath, '')
        self.__log.debug("Created file '%s'", self.__signalFilePath)

    def remove(self):
        try:
            os.remove(self.__signalFilePath)
        except Exception:
            pass
        self.__log.debug("Removed file '%s'", self.__signalFilePath)


@implementer(IServiceReferenceFactory)
class ServiceReferenceFactory(object):
    """This is a factory that builds ServiceReference objects.
    """

    def __init__(self, worker):
        """Initializes an instance of ServiceReferenceFactory.

        @param worker {ZenHubWorker}
        """
        self.__worker = worker

    def build(self, service, name, monitor):
        """Build and return a ServiceReference object.

        @param service {HubService derived} Service object
        @param name {string} Name of the service
        @param monitor {string} Name of the performance monitor (collector)
        """
        return ServiceReference(service, name, monitor, self.__worker)


class ServiceReference(pb.Referenceable):
    """
    """

    def __init__(self, service, name, monitor, worker):
        """
        """
        self.__name = name
        self.__monitor = monitor
        self.__service = service
        self.__worker = worker
        self.callStats = defaultdict(_CumulativeWorkerStats)
        self.debug = False

    @property
    def name(self):
        return self.__name

    @property
    def monitor(self):
        return self.__monitor

    @defer.inlineCallbacks
    def remoteMessageReceived(self, broker, message, args, kw):
        """
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
        """
        @param method {str} Remote method name on service.
        """
        try:
            name = self.__name.rpartition('.')[-1]
            self.__worker.current = "%s/%s" % (name, method)
            start = time.time()
            self.__worker.work_started(start)
            yield self.__service
        finally:
            finish = time.time()
            secs = finish - start
            self.callStats[method].addOccurrence(secs, finish)
            self.__service.callTime += secs
            self.__worker.work_finished(secs, method)


class _CumulativeWorkerStats(object):
    """
    Internal class for maintaining cumulative stats on frequency and runtime
    for individual methods by service
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


if __name__ == '__main__':
    zhw = ZenHubWorker(reactor)
    zhw.start()
    reactor.run()
