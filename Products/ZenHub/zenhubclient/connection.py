##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.internet import defer, task

from Products.ZenUtils.PBUtil import setKeepAlive

from .utils import getLoggerFrom


class ZenHubConnection(object):
    """Active connection to ZenHub.

    The connection to ZenHub will automatically reconnect if the connection
    fails for any reason.
    """

    def __init__(self, log, clock, service):
        """Initialize a ZenHubConnection instance.

        Note: this class assumes that service.startService() has been called.

        :param log: the logger
        :param clock: Used for scheduling calls in the reactor
        :type clock: IRreactorTime
        :param service: The connection manager
        :type service: twisted.application.internet.ClientService
        """
        self.__log = getLoggerFrom(log, self)
        self.__reactor = clock
        self.__service = service
        self.__stopping = False
        self.__pinger = None
        self.__handlers = {"connected": set(), "disconnected": set()}
        self.__connected = None
        self.__disconnected = None
        self._init_handler_deferreds()
        self._prepForConnection()

    def disconnect(self):
        """Stop connecting to ZenHub."""
        self.__stopping = True
        self._reset()

    def notifyOnConnect(self, handler):
        """Register function to be called after connecting to zenhub.

        The handler will be passed one argument which will be the
        RemoteReference object to the ZenHub server.

        NOTE: The handler is invoked each time a zenhub connection is made.
        """
        if self.__stopping:
            return
        handlers = self.__handlers["connected"]
        if handler not in handlers:
            handlers.add(handler)
            self.__connected.addCallback(handler)

    def notifyOnDisconnect(self, handler):
        """Register function to be called after losing a zenhub connection.

        The handler will be passed one argument which will be reason
        for the disconnection.

        NOTE: The handler is invoked each time a zenhub connection is lost.
        """
        if self.__stopping:
            return
        handlers = self.__handlers["disconnected"]
        if handler not in handlers:
            handlers.add(handler)
            self.__disconnected.addCallback(handler)

    def _init_handler_deferreds(self):
        # one place for initializing the event handling deferreds.
        self.__connected = defer.Deferred(canceller=_canceller)
        self.__disconnected = defer.Deferred(canceller=_canceller)
        for handler in self.__handlers["connected"]:
            self.__connected.addCallback(handler)
        for handler in self.__handlers["disconnected"]:
            self.__disconnected.addCallback(handler)

    def _prepForConnection(self):
        if not self.__stopping:
            self.__log.info("Prepping for connection")
            self.__service.whenConnected().addCallbacks(
                self._connected, self._notConnected,
            )

    def _notConnected(self, *args):
        self.__log.info("Not connected! %r", args)

    @defer.inlineCallbacks
    def _connected(self, broker):
        # Called when a connection to ZenHub is established.
        # Logs into ZenHub and passes up a worker reference for ZenHub
        # to use to dispatch method calls.

        # Sometimes broker.transport doesn't have a 'socket' attribute...
        if not hasattr(broker.transport, "socket"):
            # ...so try again
            self._restart()
            defer.returnValue(None)

        self.__log.info("Connection to ZenHub established")
        try:
            setKeepAlive(broker.transport.socket)
            zenhub = yield self._login(broker)
            ping = PingZenHub(self.__log, zenhub, self._restart)
            self.__pinger = task.LoopingCall(ping)
            d = self.__pinger.start(self.__timeout, now=False)
            d.addErrback(self._pingFail)  # Catch and pass on errors
        except defer.CancelledError:
            self.__log.error("Timed out trying to login to ZenHub")
            self._restart()
            defer.returnValue(None)
        except Exception as ex:
            self.__log.error(
                "Unable to report for work: (%s) %s",
                type(ex).__name__, ex,
            )
            raise
        else:
            self.__log.info("Logged into ZenHub")

            # Connection complete; notify connected listeners and
            # install a listener to be notified if the connection is lost.
            self.__connected.callback(broker)
            broker.notifyOnDisconnect(self._disconnected)

    def _restart(self):
        self._reset()
        self._prepForConnection()

    def _login(self, broker):
        d = broker.factory.login(self.__credentials, self.__ref)
        timeoutCall = self.__reactor.callLater(self.__timeout, d.cancel)

        def completedLogin(arg):
            if timeoutCall.active():
                timeoutCall.cancel()
            return arg

        d.addBoth(completedLogin)
        return d

    def _reset(self):
        self.__connected.cancel()
        self.__disconnected.cancel()
        self._init_handler_deferreds()
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        if self.__service:
            self.__service.stopService()
            self.__service = None

    def _disconnected(self, *args):
        # Called when the connection to ZenHub is lost.
        # Ensures that processing resumes when the connection to ZenHub
        # is restored.
        self.__log.info(
            "Lost connection to ZenHub: %s",
            args[0] if args else "<no reason given>",
        )
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        self.__disconnected.callback(args[0] if args else None)
        self._prepForConnection()

    def _pingFail(self, ex):
        self.__log.error("Pinger failed: %s", ex)


def _canceller(deferred):
    """Canceller function for Deferred objects.

    Sets the `called` attribute True so that callback and errbacks
    functions are not called.
    """
    deferred.called = True


class PingZenHub(object):
    """Simple task to ping ZenHub.

    PingZenHub's real purpose is to allow the ZenHubWorker to detect when
    ZenHub is no longer responsive (for whatever reason).
    """

    def __init__(self, log, zenhub, notify):
        """Initialize a PingZenHub instance.

        :param log: the logger
        :param zenhub: remote reference to zenhub server.
        :param notify: called when ping fails.
        """
        self.__zenhub = zenhub
        self.__notify = notify
        self.__log = getLoggerFrom(log, self)

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
            self.__notify()
