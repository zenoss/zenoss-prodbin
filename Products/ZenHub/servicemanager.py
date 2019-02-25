##############################################################################
#
# Copyright (C) Zenoss, Inc. 2018, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import os
import socket
import sys
import time

from collections import Mapping
from datetime import datetime, timedelta
from twisted.cred import portal, checkers, credentials
from twisted.internet import defer
from twisted.internet.endpoints import serverFromString
from twisted.spread import pb, banana
from twisted.web import server, xmlrpc
from zope.event import notify
from zope.interface import implementer

from Products.ZenHub import OPTION_STATE, CONNECT_TIMEOUT
from Products.ZenUtils.logger import getLogger
from Products.ZenUtils.Utils import importClass, ipv6_available

from .PBDaemon import RemoteBadMonitor, RemoteException
from .XmlRpcService import XmlRpcService
from .dispatchers import (
    DispatchingExecutor, EventDispatcher, WorkerPoolDispatcher,
    WorkerPool, ServiceCallJob, StatsMonitor
)
from .interfaces import IServiceAddedEvent
from .worklist import (
    ZenHubWorklist, ZenHubPriority, ModelingPaused,
    register_metrics_on_worklist, get_worklist_metrics
)

banana.SIZE_LIMIT = 1024 * 1024 * 10

pb.setUnjellyableForClass(RemoteBadMonitor, RemoteBadMonitor)


class HubServiceManager(object):
    """Responsible for initializing and starting the ZenHub services and
    XMLRPC servers.
    """

    def __init__(
            self, modeling_pause_timeout=None, passwordfile=None,
            pbport=None, xmlrpcport=None):
        """Initialize a HubServiceManager instance.

        @param modeling_pause_timeout {float} Duration of modeling pause
        @param passwordfile {str} Path to zenhub credentials file
        @param pbport {int} Perspective Broker server port
        @param xmlrpcport {int} XMLRPC server port
        """
        if modeling_pause_timeout is None:
            self.__raiseMissingKeywordError("modeling_pause_timeout")
        self.__modeling_pause_timeout = modeling_pause_timeout

        if passwordfile is None:
            self.__raiseMissingKeywordError("passwordfile")
        self.__passwdfile = passwordfile

        if pbport is None:
            self.__raiseMissingKeywordError("pbport")
        self.__pbport = pbport

        if xmlrpcport is None:
            self.__raiseMissingKeywordError("xmlrpcport")
        self.__xmlrpcport = xmlrpcport

        self.__workers = None
        self.__services = None  # set in 'start'
        self.__xmlrpc_site = None  # set in 'start'
        self.__log = getLogger("zenhub", self)

    def start(self, dmd, reactor):
        """Start the servers.

        @param dmd {dmd} The dmd reference
        @param reactor {IReactor} Twisted reactor instance
        """
        # Finish initialization
        modeling_paused = ModelingPaused(dmd, self.__modeling_pause_timeout)
        self.__worklist = ZenHubWorklist(modeling_paused=modeling_paused)

        # configure Metrology for the worklists
        register_metrics_on_worklist(self.__worklist)

        self.__workers = WorkerPool()
        self.__stats = StatsMonitor()
        self.__workerdispatcher = WorkerPoolDispatcher(
            reactor, self.__worklist, self.__workers, self.__stats
        )
        events = EventDispatcher(dmd.ZenEventManager)
        executor = DispatchingExecutor(
            [events], default=self.__workerdispatcher
        )
        service_factory = WorkerInterceptorFactory(executor)
        self.__services = HubServiceRegistry(dmd, service_factory)

        # Start the Perspective Broker server
        avatar = HubAvatar(self.__services, self.__workers)
        realm = HubRealm(avatar)
        checkers = getCredentialCheckers(self.__passwdfile)
        hubportal = portal.Portal(realm, checkers)
        hubserver_factory = pb.PBServerFactory(hubportal)
        tcp_version = "tcp6" if ipv6_available() else "tcp"
        pb_descriptor = "%s:port=%s" % (tcp_version, self.__pbport)
        pb_server = serverFromString(reactor, pb_descriptor)

        dfr = pb_server.listen(hubserver_factory)
        dfr.addCallback(self.__setKeepAlive)

        # Initialize and start the XMLRPC server
        self.__xmlrpc_site = AuthXmlRpcService.makeSite(dmd, checkers)
        xmlrpc_descriptor = "%s:port=%s" % (tcp_version, self.__xmlrpcport)
        xmlrpc_server = serverFromString(reactor, xmlrpc_descriptor)
        xmlrpc_server.listen(self.__xmlrpc_site)

    @property
    def services(self):
        return self.__services

    @property
    def worklist(self):
        return self.__worklist

    def onExecute(self, listener):
        """Register a listener that will be called prior the execution of
        a job on a worker.

        @param listener {callable}
        """
        self.__workerdispatcher.onExecute(listener)

    @defer.inlineCallbacks
    def reportWorkerStatus(self):
        yield self.__workerdispatcher.reportWorkerStatus()

    def getStatusReport(self):
        now = time.time()

        gauges = get_worklist_metrics(self.__worklist)
        workTracker, execTimer = (self.__stats.workers, self.__stats.jobs)

        lines = ["Worklist Stats:"]
        lines.extend(
            "   {:<22}: {}".format(priority, gauges[key])
            for priority, key in (
                ("Events", ZenHubPriority.EVENTS),
                ("Other", ZenHubPriority.OTHER),
                ("ApplyDataMaps (batch)", ZenHubPriority.MODELING),
                ("ApplyDataMaps (single)", ZenHubPriority.SINGLE_MODELING),
            )
        )

        lines.extend([
            "   {:<22}: {}".format("Total", sum(v for v in gauges.values())),
            "",
            "Hub Execution Timings:",
            "   {:<32} {:>8} {:>12} {:>13}  {} ".format(
                "method", "count", "idle_total",
                "running_total", "last_called_time"
            )
        ])

        statline = " - {:<32} {:>8} {:>12} {:>13}  {:%Y-%m-%d %H:%M:%S}"
        sorted_by_running_total = sorted(
            execTimer.iteritems(), key=lambda e: -(e[1].running_total)
        )
        lines.extend(
            statline.format(
                method, stats.count,
                timedelta(seconds=round(stats.idle_total)),
                timedelta(seconds=round(stats.running_total)),
                datetime.fromtimestamp(stats.last_called_time)
            )
            for method, stats in sorted_by_running_total
        )

        lines.extend([
            "",
            "Worker Stats:"
        ])
        nostatsFmt = "    {:>2}:Idle [] No jobs run"
        statsFmt = "    {:>2}:{} [{}  Idle: {}] {}"
        lines.extend(
            statsFmt.format(
                workerId, stats.status, stats.description,
                timedelta(seconds=round(stats.previdle)),
                timedelta(seconds=round(now - stats.lastupdate))
            )
            if stats else nostatsFmt.format(workerId)
            for workerId, stats in sorted(workTracker.iteritems())
        )
        return '\n'.join(lines)

    def __setKeepAlive(self, pbport):
        sock = pbport.socket
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, OPTION_STATE)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, CONNECT_TIMEOUT)
        interval = max(CONNECT_TIMEOUT / 4, 10)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, interval)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 2)
        self.__log.debug(
            "set socket%s  CONNECT_TIMEOUT:%d  TCP_KEEPINTVL:%d",
            sock.getsockname(), CONNECT_TIMEOUT, interval
        )

    def __raiseMissingKeywordError(self, name):
        raise TypeError(
            "%s.__init__ missing expected keyword argument: %s" % (
                type(self).__name__, name
            )
        )


@implementer(portal.IRealm)
class HubRealm(object):
    """
    Following the Twisted authentication framework.
    See http://twistedmatrix.com/projects/core/documentation/howto/cred.html
    """

    def __init__(self, avatar):
        self.__avatar = avatar

    def requestAvatar(self, name, mind, *interfaces):
        if pb.IPerspective not in interfaces:
            raise NotImplementedError
        return pb.IPerspective, self.__avatar, lambda: None


class HubAvatar(pb.Avatar):
    """Manages the connection between clients and ZenHub.
    """

    def __init__(self, services, workers):
        """Initialize an instance of HubAvatar.

        @param services {HubServiceManager} ZenHub's service manager
        @param workers {WorkerPool} Manages references to workers.
        """
        self.__services = services
        self.__workers = workers
        self.__log = getLogger("zenhub", self)

    def perspective_ping(self):
        return 'pong'

    def perspective_getHubInstanceId(self):
        return os.environ.get('CONTROLPLANE_INSTANCE_ID', 'Unknown')

    def perspective_getService(
            self, name, monitor=None, listener=None, options=None):
        """
        Allow a collector to find a Hub service by name.  It also
        associates the service with a collector so that changes can be
        pushed back out to collectors.

        @param name {string} The name of the service, e.g. "EventService"
        @param monitor {string} The name of a collector, e.g. "localhost"
        @param listener {RemoteReference} A remote reference to the client
        @return {WorkerInterceptor} A reference to a service
        """
        try:
            service = self.__services.getService(name, monitor)
        except RemoteBadMonitor:
            # This is a valid remote exception, so let it go through
            # to the collector daemon to handle
            raise
        except UnknownServiceError:
            self.__log.error("Service '%s' not found", name)
            raise
        except Exception as ex:
            self.__log.exception("Failed to get service '%s'", name)
            raise pb.Error(str(ex))
        else:
            if service is not None and listener:
                service.addListener(listener, options)
            return service

    def perspective_reportingForWork(self, worker, workerId):
        """
        Allow a worker register for work.

        @param worker {RemoteReference} Reference to zenhubworker
        @return None
        """
        worker.busy = False
        worker.workerId = workerId
        self.__log.info("Worker %s reporting for work", workerId)
        try:
            self.__workers.add(worker)
        except Exception as ex:
            self.__log.exception("Failed to add worker %s", workerId)
            raise pb.Error(
                "Internal ZenHub error: %s: %s" % (ex.__class__, ex)
            )

        def removeWorker(worker):
            if worker in self.__workers:
                self.__workers.remove(worker)
                self.__log.info("Worker %s disconnected", worker.workerId)

        worker.notifyOnDisconnect(removeWorker)


class HubServiceRegistry(Mapping):
    """A registry of ZenHub service objects.

    HubServiceRegistry does lazy loading of services, i.e. a service is
    not loaded until requested.
    """

    def __init__(self, dmd, factory):
        """Initialize a HubServiceRegistry instance.

        @param dmd {dmd} The ZODB dmd object.
        @param factory {WorkerInterceptorFactory}
            Builds WorkerInterceptor objects.
        """
        self.__dmd = dmd
        self.__factory = factory
        self.__services = {}

    def __iter__(self):
        return iter(self.__services)

    def __len__(self):
        return len(self.__services)

    def __getitem__(self, key):
        return self.__services[key]

    def getService(self, name, monitor):
        """Returns (a Referenceable to) the named service.

        The name of the service should be the fully qualified module path
        containing the class implementing the service.  For example,

            ZenPacks.zenoss.PythonCollector.services.PythonConfig

        is a fully qualified module path to the PythonConfig zenhub service.
        A class named 'PythonConfig' is expected to be found within the
        module 'PythonConfig'.

        Services found in Products.ZenHub.services can by referred to by
        just their module name.  For example, 'EventService' may be used
        instead of 'Products.ZenHub.services.EventService' to retrieve the
        event service.

        If the service cannot be found, an UnknownServiceError is raised.

        The 'monitor' parameter must be the name of an existing performance
        monitor (aka collector).  If the monitor is unknown, a RemoteBadMonitor
        exception is raised.

        @type name {str} Name of the service
        @type monitor {str} Name of a performance monitor
        @return {WorkerInterceptor} A Referenceable to the service.
        """
        # Sanity check the names given to us
        if not self.__dmd.Monitors.Performance._getOb(monitor, False):
            raise RemoteBadMonitor(
                "Unknown performance monitor: '%s'" % (monitor,), None
            )

        svc = self.__services.get((name, monitor))
        if svc is None:
            return self.__addservice(name, monitor)
        return svc

    def __addservice(self, name, monitor):
        try:
            cls = importClass(name)
        except ImportError:
            try:
                cls = importClass("Products.ZenHub.services.%s" % name, name)
            except ImportError:
                raise UnknownServiceError(str(name))
        try:
            # Will it construct/initialize?
            svc = cls(self.__dmd, monitor)
        except Exception:
            # Module can't be used, so unload it.
            if cls.__module__ in sys.modules:
                del sys.modules[cls.__module__]
            raise
        else:
            svc = self.__factory.build(svc, name, monitor)
            self.__services[name, monitor] = svc
            notify(ServiceAddedEvent(name, monitor))
            return svc


@implementer(IServiceAddedEvent)
class ServiceAddedEvent(object):

    def __init__(self, name, instance):
        """Initialize a ServiceAddedEvent instance.

        @param name {str} Name of the service.
        @param instance {str} Name of the performance monitor (collector).
        """
        self.name = name
        self.instance = instance


class UnknownServiceError(pb.Error):
    """Raised if the requested service doesn't exist.
    """


class WorkerInterceptorFactory(object):
    """This is a factory that builds WorkerInterceptor objects.
    """

    def __init__(self, dispatcher):
        """Initializes an instance of WorkerInterceptorFactory.

        @param dispatcher {IAsyncDispatch} Executes service calls
        """
        self.__dispatcher = dispatcher

    def build(self, service, name, monitor):
        """Build and return a WorkerInterceptor object.

        @param name {string} Name of the service
        @param monitor {string} Name of the performance monitor (collector)
        """
        return WorkerInterceptor(service, name, monitor, self.__dispatcher)


# Note: The name 'WorkerInterceptor' is required to remain compatible with
# the EnterpriseCollector zenpack.
class WorkerInterceptor(pb.Referenceable):
    """The WorkerInterceptor extends a Referenceable to delegate message
    handling to an executor.
    """

    def __init__(self, service, name, monitor, executor):
        """Initializes an instance of WorkerInterceptor.

        @param service {HubService subclass} The service object.
        @param name {str} Name of the service.
        @param monitor {str} Name of the caller's collection monitor.
        @param executor {IAsyncDispatch} Handles the message/method call.
        """
        self.__service = service
        self.__name = name
        self.__monitor = monitor
        self.__executor = executor
        self.__log = getLogger("zenhub", self)
        self.callTime = 0.0

    @property
    def service(self):
        return self.__service

    @defer.inlineCallbacks
    def remoteMessageReceived(self, broker, message, args, kw):
        begin = time.time()
        try:
            args = broker.unserialize(args)
            kw = broker.unserialize(kw)
            job = ServiceCallJob(
                self.__name, self.__monitor, message, args, kw
            )
            self.__log.info(
                "Calling %s.%s from %s", self.__name, message, self.__monitor
            )
            state = yield self.__executor.submit(job)
            response = broker.serialize(state, self.perspective)
            defer.returnValue(response)
        except (pb.Error, pb.RemoteError, RemoteException):
            self.__log.info(
                "Called  %s.%s from %s [failure]",
                self.__name, message, self.__monitor
            )
            raise  # propagate these exceptions
        except Exception as ex:
            self.__log.exception('Failed to handle remote procedure call')
            raise pb.Error("Internal ZenHub error: %r" % (ex,))
        finally:
            end = time.time()
            self.callTime += (end - begin)
            self.__log.info(
                "Called  %s.%s from %s", self.__name, message, self.__monitor
            )

    def __getattr__(self, attr):
        """Forward calls to the service object.
        """
        return getattr(self.__service, attr)


class AuthXmlRpcService(XmlRpcService):
    """Extends XmlRpcService to provide authentication.
    """

    @classmethod
    def makeSite(cls, dmd, checker):
        service = cls(dmd, checker)
        return server.Site(service)

    def __init__(self, dmd, checker):
        """Initializes an AuthXmlRpcService instance.

        @param dmd {DMD} A /zport/dmd reference
        @param checker {ICredentialsChecker} Used to authenticate clients.
        """
        XmlRpcService.__init__(self, dmd)
        self.checker = checker

    def doRender(self, unused, request):
        """
        Call the inherited render engine after authentication succeeds.
        See @L{XmlRpcService.XmlRpcService.Render}.
        """
        return XmlRpcService.render(self, request)

    def unauthorized(self, request):
        """
        Render an XMLRPC error indicating an authentication failure.
        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: None
        """
        self._cbRender(xmlrpc.Fault(self.FAILURE, "Unauthorized"), request)

    def render(self, request):
        """
        Unpack the authorization header and check the credentials.
        @type request: HTTPRequest
        @param request: the request for this xmlrpc call.
        @return: NOT_DONE_YET
        """
        auth = request.getHeader('authorization')
        if not auth:
            self.unauthorized(request)
        else:
            try:
                type, encoded = auth.split()
                if type not in ('Basic',):
                    self.unauthorized(request)
                else:
                    user, passwd = encoded.decode('base64').split(':')
                    c = credentials.UsernamePassword(user, passwd)
                    d = self.checker.requestAvatarId(c)
                    d.addCallback(self.doRender, request)

                    def error(unused, request):
                        self.unauthorized(request)

                    d.addErrback(error, request)
            except Exception:
                self.unauthorized(request)
        return server.NOT_DONE_YET


def getCredentialCheckers(pwdfile):
    """
    Load the password file

    @return: an object satisfying the ICredentialsChecker
    interface using a password file or an empty list if the file
    is not available.  Uses the file specified in the --passwd
    command line option.
    """
    checker = checkers.FilePasswordDB(pwdfile)
    return [checker]
