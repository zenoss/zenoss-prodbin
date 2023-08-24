##############################################################################
#
# Copyright (C) Zenoss, Inc. 2023, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging

from twisted.application.internet import ClientService, backoffPolicy
from twisted.cred.credentials import UsernamePassword
from twisted.internet import defer, reactor, task
from twisted.internet.endpoints import clientFromString

from Products.ZenHub.server import ZenPBClientFactory
from Products.ZenUtils.PBUtil import setKeepAlive

log = logging.getLogger("zen.zenhubclient")


class ZenHubClient(object):
    """A client for connecting to ZenHub.

    After start is called, this class automatically handles connecting to
    ZenHub, registering the collection daemon with ZenHub, and automatically
    reconnecting to ZenHub if the connection to ZenHub is corrupted for
    any reason.
    """

    @classmethod
    def make(cls, username, passwd, host, port, timeout):
        creds = UsernamePassword(username, passwd)
        descriptor = "tcp:{host}:{port}".format(host=host, port=port)
        endpoint = clientFromString(reactor, descriptor)
        return cls(reactor, endpoint, creds, timeout)

    def __init__(self, reactor, endpoint, credentials, timeout):
        """Initialize a ZenHubClient instance.

        The `connected` function is a invoked when a connection to ZenHub
        has been established.  A reference to ZenHub proxy is passed as the
        argument to the function.  The `connected` function may return a
        Deferred object.  Any other return value is ignored.

        The `connectionlost` function is invoked when the ZenHub connection
        is lost.  No arguments are passed in.  The return value is ignored.

        :type reactor: IReactorCore
        :param endpoint: Where zenhub is found
        :type endpoint: IStreamClientEndpoint
        :param credentials: Credentials to log into ZenHub.
        :type credentials: IUsernamePassword
        :param timeout: Seconds until deciding that ZenHub is not responsive.
        :type timeout: float
        """
        self.__reactor = reactor
        self.__endpoint = endpoint
        self.__credentials = credentials
        self.__timeout = timeout
        self.__on_connection = None
        self.__on_connection_lost = None

        self.__stopping = False
        self.__pinger = None
        self.__connection = None

    def start(self, onconnect=None, ondisconnect=None):
        """
        Begin the connection to ZenHub.

        :param onconnect: Called when a connection to ZenHub is established
        :type onconnect: Callable[ZenHubProxy, Deferred | Any]
        :param ondisconnect: Called when the ZenHub connection is lost
        :type ondisconnect: Callable[]
        """
        self.__on_connection = onconnect
        self.__on_connection_lost = ondisconnect
        self.__stopping = False
        factory = ZenPBClientFactory()
        self.__connection = ClientService(
            self.__endpoint,
            factory,
            retryPolicy=backoffPolicy(initialDelay=0.5, factor=3.0),
        )
        self.__connection.startService()
        self.__prepForConnection()

    def stop(self):
        """Stop the connection to ZenHub."""
        self.__stopping = True
        self.__reset()

    def restart(self):
        """Restart the connection to ZenHub."""
        self.__reset()
        self.start()

    def __reset(self):
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None
        if self.__connection:
            self.__connection.stopService()
            self.__connection = None

    def __prepForConnection(self):
        if not self.__stopping:
            log.info("Prepping for connection")
            self.__connection.whenConnected().addCallbacks(
                self.__connected, self.__notConnected
            )

    def __disconnected(self, *args):
        # Called when the connection to ZenHub is lost.
        # Ensures that processing resumes when the connection to ZenHub
        # is restored.
        log.info(
            "Lost connection to ZenHub: %s",
            args[0] if args else "<no reason given>",
        )
        if self.__pinger:
            self.__pinger.stop()
            self.__pinger = None

        # Call the user supplied callback function.
        if self.__on_connection_lost:
            self.__on_connection_lost()

        self.__prepForConnection()

    def __notConnected(self, *args):
        log.info("Not connected! %r", args)

    @defer.inlineCallbacks
    def __connected(self, broker):
        # Called when a connection to ZenHub is established.

        # Sometimes broker.transport doesn't have a 'socket' attribute
        if not hasattr(broker.transport, "socket"):
            self.restart()
            defer.returnValue(None)

        log.info("Connection to ZenHub established")
        try:
            setKeepAlive(broker.transport.socket)

            zenhub = yield self.__login(broker)

            ping = PingZenHub(zenhub, self)
            self.__pinger = task.LoopingCall(ping)
            d = self.__pinger.start(self.__timeout, now=False)
            d.addErrback(self.__pingFail)  # Catch and pass on errors
        except defer.CancelledError:
            log.error("Timed out trying to login to ZenHub")
            self.restart()
            defer.returnValue(None)
        except Exception as ex:
            log.error(
                "Unable to report for work: (%s) %s", type(ex).__name__, ex
            )
            self.__reactor.stop()
        else:
            log.info("Logged into ZenHub")

            # Connection complete; install a listener to be notified if
            # the connection is lost.
            broker.notifyOnDisconnect(self.__disconnected)

            # Schedule the user supplied callback function to run.
            if self.__on_connection:
                self.__reactor.callLater(
                    0, defer.maybeDeferred(self.__on_connection(zenhub))
                )

    def __login(self, broker):
        d = broker.factory.login(self.__credentials)
        timeoutCall = self.__reactor.callLater(self.__timeout, d.cancel)

        def completedLogin(arg):
            if timeoutCall.active():
                timeoutCall.cancel()
            return arg

        d.addBoth(completedLogin)
        return d

    def __pingFail(self, ex):
        log.error("Pinger failed: %s", ex)


class PingZenHub(object):
    """Simple task to ping ZenHub.

    PingZenHub's real purpose is to allow the ZenHubWorker to detect when
    ZenHub is no longer responsive (for whatever reason).
    """

    def __init__(self, zenhub, client):
        """Initialize a PingZenHub instance."""
        self.__zenhub = zenhub
        self.__client = client

    @defer.inlineCallbacks
    def __call__(self):
        """Ping zenhub.

        If the ping fails, causes the connection to ZenHub to reset.
        """
        log.debug("Pinging zenhub")
        try:
            response = yield self.__zenhub.callRemote("ping")
            log.debug("Pinged  zenhub: %s", response)
        except Exception as ex:
            log.error("Ping failed: %s", ex)
            self.__client.restart()
