##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import collections
import logging
import importlib
import os
import sys

import six

from twisted.application.internet import backoffPolicy, ClientService
from twisted.internet import defer, task
from twisted.spread import pb

from Products.ZenUtils.PBUtil import setKeepAlive
from Products.ZenUtils.Utils import zenPath, atomicWrite

from .errors import HubDown
from .server import ZenPBClientFactory

log = logging.getLogger("zen.zenhubclient")


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
        app,
        timeout,
        ping_interval,
    ):
        """Initialize a ZenHubClient instance.

        :type reactor: IReactorCore
        :param endpoint: Where zenhub is found
        :type endpoint: IStreamClientEndpoint
        :param credentials: Credentials to log into ZenHub.
        :type credentials: IUsernamePassword
        :param app: Reference to the application object.
        :type app: pb.Referenceable
        :param float timeout: Seconds to wait before determining whether
            ZenHub is unresponsive.
        :param float ping_interval: Ping ZenHub every n seconds
        """
        self.__reactor = reactor
        self.__endpoint = endpoint
        self.__credentials = credentials
        self.__app = app
        self.__timeout = timeout
        self.__ping_interval = ping_interval

        self.__stopping = False
        self.__service = ClientService(
            self.__endpoint,
            ZenPBClientFactory(),
            retryPolicy=_getBackoffPolicy(initialDelay=0.5, factor=3.0),
            prepareConnection=self._new_connection,
        )
        self.__services = {}
        self.__connected_callbacks = []
        self.__disconnected_callbacks = []

        self.__pinger = None
        self.__zenhub = None
        self.__instanceId = None
        self.__signalFile = ConnectedToZenHubSignalFile()

    @property
    def instance_id(self):
        # type: () -> str
        """
        Return ZenHub's Control Center instance ID.

        The value is a string containing a number or "unknown".
        """
        return self.__instanceId

    @property
    def services(self):
        # type: () -> collections.Mapping[str, pb.Referenceable]
        return _FrozenDictProxy(self.__services)

    def start(self):
        # type: () -> defer.Deferred
        """
        Start connecting to ZenHub.

        On a successful connection, the returned Deferred's callback is
        invoked with the ZenHub broker instance.  On failure, the errback
        is invoked with the error.

        :rtype: defer.Deferred
        """
        if self.__service.running:
            log.warn("service already running  service=%r", self.__service)
            return
        self.__service.startService()
        log.debug("started client service  service=%r", self.__service)
        return self.__service.whenConnected()

    def stop(self):
        # type: () -> defer.Deferred
        """
        Stop connecting to ZenHub.

        When the connection is closed, the returned Deferred is called.

        :rtype: defer.Deferred
        """
        self.__stopping = True
        self._reset()
        return self.__service.stopService()

    def notifyOnConnect(self, f):
        self.__connected_callbacks.append(f)

    def notifyOnDisconnect(self, f):
        self.__disconnected_callbacks.append(f)

    @defer.inlineCallbacks
    def ping(self):
        response = yield self.__zenhub.callRemote("ping")
        defer.returnValue(response)

    @defer.inlineCallbacks
    def register_worker(self, worker, instanceId, worklistId):
        try:
            yield self.__zenhub.callRemote(
                "reportingForWork",
                worker,
                workerId=instanceId,
                worklistId=worklistId,
            )
        except pb.RemoteError as ex:
            six.reraise(_remoteErrorType(ex), ex.args[0], tb=sys.exc_info()[2])

    @defer.inlineCallbacks
    def get_service(self, name, monitor, listener, options):
        # type: (str, str, object, collections.Mapping) -> defer.Deferred
        """
        Return a reference to the named ZenHub service.

        :param name: Name of the service
        :param monitor: Name of the collector
        :param listener: Object reference to caller
        :param options: key/value data relevant to the service
        """
        if name in self.__services:
            defer.returnValue(self.__services[name])

        if self.__zenhub is None:
            raise HubDown("not connected to ZenHub")

        try:
            service_ref = yield self.__zenhub.callRemote(
                "getService", name, monitor, listener, options
            )
            self.__services[name] = service_ref
            log.debug(
                "retrieved remote reference to ZenHub service  "
                "name=%s monitor=%s service=%r",
                name,
                monitor,
                service_ref,
            )
            defer.returnValue(service_ref)
        except pb.RemoteError as ex:
            six.reraise(_remoteErrorType(ex), ex.args[0], tb=sys.exc_info()[2])

    @defer.inlineCallbacks
    def _new_connection(self, broker):
        log.debug("connected to ZenHub  broker=%r", broker)
        try:
            if hasattr(broker.transport, "socket"):
                setKeepAlive(broker.transport.socket)
            else:
                log.warn("broker.transport.socket attribute is missing")

            self.__zenhub = yield self._login(broker)

            ping = PingZenHub(self.__zenhub, self)
            self.__pinger = task.LoopingCall(ping)
            d = self.__pinger.start(self.__ping_interval, now=False)
            d.addErrback(self._pingFail)  # Catch and pass on errors
            log.debug("started ZenHub pinger  pinger=%r", self.__pinger)

            self.__instanceId = yield self.__zenhub.callRemote(
                "getHubInstanceId"
            )
        except defer.CancelledError:
            log.error("timed out trying to login to ZenHub")
            self._reset()
            raise RuntimeError("reject connection")
        except pb.RemoteError as ex:
            log.error("login rejected by ZenHub: %s", _fromRemoteError(ex))
            self._reset()
            raise RuntimeError("reject connection")
            # defer.returnValue(None)
        except Exception:
            log.exception("unexpected error while logging into ZenHub")
            self.__signalFile.remove()
            self.__reactor.stop()
        else:
            log.debug("logged into ZenHub  instance-id=%s", self.__instanceId)
            try:
                self.__signalFile.touch()
                # Connection complete; install a listener to be notified if
                # the connection is lost.
                broker.notifyOnDisconnect(self._disconnected)

                log.debug(
                    "calling %d on-connect callbacks",
                    len(self.__connected_callbacks),
                )
                for callback in self.__connected_callbacks:
                    try:
                        yield defer.maybeDeferred(callback)
                    except Exception:
                        log.exception(
                            "disconnect callback error  callback=%r", callback
                        )
            except Exception:
                log.exception("boom")

    def _login(self, broker):
        d = broker.factory.login(self.__credentials, self.__app)
        timeoutCall = self.__reactor.callLater(self.__timeout, d.cancel)

        def completedLogin(arg):
            if timeoutCall.active():
                timeoutCall.cancel()
            return arg

        d.addBoth(completedLogin)
        return d

    def _disconnected(self, *args):
        # Called when the connection to ZenHub is lost.
        # Ensures that processing resumes when the connection to ZenHub
        # is restored.
        log.warn(
            "disconnected from ZenHub%s",
            ": %s" % (args[0],) if args else "",
        )
        self._reset()
        for callback in self.__disconnected_callbacks:
            try:
                callback(*args)
            except Exception:
                log.exception(
                    "disconnect callback error  callback=%r", callback
                )
        self.__disconnected_callbacks = []

    def _reset(self):
        self.__zenhub = None
        self.__services = {}
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
            log.debug("stopped and removed ZenHub pinger")
        self.__signalFile.remove()

    def _pingFail(self, ex):
        log.error("pinger failed: %s", ex)


class PingZenHub(object):
    """Simple task to ping ZenHub.

    PingZenHub's real purpose is to allow the ZenHubWorker to detect when
    ZenHub is no longer responsive (for whatever reason).
    """

    def __init__(self, zenhub, client):
        """Initialize a PingZenHub instance."""
        self.__zenhub = zenhub
        self.__client = client
        self.__log = log.getChild("ping")

    @defer.inlineCallbacks
    def __call__(self):
        # type: () -> defer.Deferred
        """Ping zenhub.

        If the ping fails, causes the connection to ZenHub to reset.
        """
        try:
            response = yield self.__zenhub.callRemote("ping")
            self.__log.debug("pinged  zenhub: %s", response)
        except Exception as ex:
            self.__log.error("ping failed: %s", ex)


class _FrozenDictProxy(collections.Mapping):
    def __init__(self, data):
        self.__data = data

    def __getitem__(self, key):
        return self.__data[key]

    def __contains__(self, key):
        return key in self.__data

    def __len__(self):
        return len(self.__data)

    def __iter__(self):
        return iter(self.__data)


def _getBackoffPolicy(*args, **kw):
    policy = backoffPolicy(*args, **kw)

    def _policy(attempt):
        log.info(
            "no connection to ZenHub; is ZenHub running?  attempt=%s", attempt
        )
        return policy(attempt)

    return _policy


def _remoteErrorType(ex):
    modpath, clsname = ex.remoteType.rsplit(".", 1)
    mod = importlib.import_module(modpath)
    return getattr(mod, clsname)


def _fromRemoteError(ex):
    return _remoteErrorType(ex)(*ex.args)


class ConnectedToZenHubSignalFile(object):
    """Manages a file that indicates successful connection to ZenHub."""

    def __init__(self):
        """Initialize a ConnectedToZenHubSignalFile instance."""
        filename = "zenhub_connected"
        self.__signalFilePath = zenPath("var", filename)
        self.__log = log.getChild("signalfile")

    def touch(self):
        """Create the file."""
        atomicWrite(self.__signalFilePath, "")
        self.__log.debug("Created file '%s'", self.__signalFilePath)

    def remove(self):
        """Delete the file."""
        try:
            os.remove(self.__signalFilePath)
        except Exception:
            pass
        self.__log.debug("Removed file '%s'", self.__signalFilePath)
