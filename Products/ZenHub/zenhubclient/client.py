##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

import logging

from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet import defer, task

from Products.ZenUtils.PBUtil import setKeepAlive

from ..server import ZenPBClientFactory


class ZenHubClient(object):
    """A client for connecting to ZenHub as a collection daemon.

    After start is called, this class automatically handles connecting to
    ZenHub, registering the zenhubworker with ZenHub, and automatically
    reconnecting to ZenHub if the connection to ZenHub is corrupted for
    any reason.
    """

    @classmethod
    def connect(cls, reactor, endpoint, credentials, worker, timeout):
        """Connect to ZenHub.

        Returns a Deferred object that fires when the connection to zenhub
        has completed.  Callbacks are given an instance of ZenHubClient
        that can be used to interact with ZenHub.

        :type reactor: IReactorCore
        :param endpoint: Where zenhub is found
        :type endpoint: IStreamClientEndpoint
        :param credentials: Credentials to log into ZenHub.
        :type credentials: IUsernamePassword
        :param worker: Reference to worker
        :type worker: IReferenceable
        :param float timeout: Seconds to wait before determining whether
            ZenHub is unresponsive.
        """
        client = cls(reactor, endpoint, credentials, worker, timeout)
        dfr = client.start()
        return dfr

    def __init__(self, reactor, endpoint, credentials, worker, timeout):
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
        """
        self.__reactor = reactor
        self.__endpoint = endpoint
        self.__credentials = credentials
        self.__worker = worker
        self.__timeout = timeout

        self.__stopping = False
        self.__pinger = None
        self.__service = None
        self.__zenhub = None

        self.__log = logging.getLogger("zen.zenhubclient")

    def start(self):
        """Start connecting to ZenHub.

        Returns a Deferred object that fires when the zenhub connection
        is achieved.  The ZenHubClient is passed as the success value.
        """
        self.__stopping = False
        factory = ZenPBClientFactory()
        self.__service = ClientService(
            self.__endpoint, factory,
            retryPolicy=backoffPolicy(initialDelay=0.5, factor=3.0),
        )
        self.__service.startService()
        d = defer.Deferred()
        self.__prepForConnection(d)
        return d

    def stop(self):
        """Stop connecting to ZenHub."""
        self.__stopping = True
        self.__reset()
        self.__zenhub = None

    def restart(self):
        """Restart the connect to ZenHub."""
        self.__reset()
        self.start()

    def getService(self, name, monitor, *args, **kw):
        """Retrieve a remote reference to a ZenHub service.

        Returns a Deferred that fires when the service has been retrieved.
        A remote reference to the service is passed to the callback.

        :param str name: The name of the service
        :param str monitor: The name of the collector
        """
        return self.__zenhub.callRemote("getService", *args, **kw)

    def reportForWork(self, worker, workerid, worklistid):
        """Register the worker with ZenHub to work on tasks from worklistid.

        Returns a Deferred that fires when the worker has been registered.

        :param worker: Reference to the worker
        :type worker: pb.Referenceable
        :param str workerid: An identity the worker uses for itself
        :param str worklistid: The name of the ZenHub worklist.
        """
        return self.__zenhub.callRemote(
            "reportingForWork",
            self.__worker, workerId=workerid, worklistId=worklistid
        )

    def __reset(self):
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        if self.__service:
            self.__service.stopService()
            self.__service = None
        if self.__zenhub:
            self.__zenhub = None

    def __prepForConnection(self, user_d=None):
        if not self.__stopping:
            self.__log.info("Prepping for connection")
            when = self.__service.whenConnected()
            if user_d:
                when.addCallback(self.__connected, user_d)
            else:
                when.addCallback(self.__connected)
            when.addErrback(self.__notConnected)

    def __disconnected(self, *args):
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
        self.__prepForConnection()

    def __notConnected(self, *args):
        self.__log.info("Not connected! %r", args)

    @defer.inlineCallbacks
    def __connected(self, broker, user_d=None):
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

            self.__zenhub = yield self.__login(broker)

            ping = PingZenHub(self.__zenhub, self)
            self.__pinger = task.LoopingCall(ping)
            pinger_dfr = self.__pinger.start(self.__timeout, now=False)
            pinger_dfr.addErrback(self.__pingFail)  # Catch and pass on errors
        except defer.CancelledError:
            self.__log.error("Timed out trying to login to ZenHub")
            self.restart()
            defer.returnValue(None)
        else:
            self.__log.info("Logged into ZenHub")

            # Connection complete; install a listener to be notified if
            # the connection is lost.
            broker.notifyOnDisconnect(self.__disconnected)
            if user_d is not None:
                user_d.callback(self)
            defer.returnValue(self)

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
        """Initialize a PingZenHub instance."""
        self.__zenhub = zenhub
        self.__client = client
        self.__log = logging.getLogger("zen.zhc.pingzenhub")

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
