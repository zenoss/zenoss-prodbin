##############################################################################
#
# Copyright (C) Zenoss, Inc. 2019 all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from twisted.application.internet import ClientService, backoffPolicy
from twisted.cred.credentials import UsernamePassword
from twisted.internet.endpoints import clientFromString

from Products.ZenHub import PB_PORT
from Products.ZenHub.server import ZenPBClientFactory

from .connection import ZenHubConnection

DEFAULT_TIMEOUT = 30.0


def connect(**kw):
    """Return a ZenHubConnection object."""


class ZenHubClientFactory(object):
    """A factory for creating connections to ZenHub.

    After start is called, this class automatically handles connecting to
    ZenHub, automatically reconnecting to ZenHub if the connection to
    ZenHub is corrupted for any reason.
    """

    @classmethod
    def create(
        cls,
        log=None,
        reactor=None,
        host=None, port=PB_PORT,
        user=None, passwd=None,
        ref=None,
        timeout=DEFAULT_TIMEOUT,
    ):
        """Return a new ZenHubClient instance.

        This classmethod accepts general parameters that are used
        to initialize a ZenHubClient instance.

        :param log: The logger instance
        :param reactor: The twisted reactor to use
        :type reactor: IReactorCore
        :param host: The host where zenhub runs
        :param port: The port zenhub listens on
        :param user: The user to log into zenhub as
        :param passwd: The password for the user
        :param ref: The referencable object to share with zenhub
        :param timeout: Duration until a successful zenhub connection.
        """
        required = ("log", "reactor", "host", "user", "passwd", "ref")
        _locals = locals()
        missing = [
            p
            for p in required
            if p not in _locals or _locals[p] is None
        ]
        if len(missing) > 0:
            raise TypeError(
                "ZenHubClient missing required arguments: %s",
                ", ".join(missing)
            )
        creds = UsernamePassword(user, passwd)
        endpointDescriptor = \
            "tcp:{host}:{port}".format(host=host, port=port)
        endpoint = clientFromString(reactor, endpointDescriptor)
        return cls(endpoint, creds, ref, timeout)

    def __init__(self, log, endpoint, credentials, ref, timeout):
        """Initialize a ZenHubClient instance.

        :param log: the logger
        :param endpoint: Where zenhub is found
        :type endpoint: IStreamClientEndpoint
        :param credentials: Credentials to log into ZenHub.
        :type credentials: IUsernamePassword
        :param ref: Local Referenceable to share with ZenHub
        :type worker: IReferenceable
        :param float timeout: Seconds to wait before determining whether
            ZenHub is unresponsive.
        """
        self.__endpoint = endpoint
        self.__credentials = credentials
        self.__ref = ref
        self.__timeout = timeout

        self.__log = log

    def connect(self, clock):
        """Connect to ZenHub.

        :param clock: Used for scheduling calls in the reactor
        :type clock: IRreactorTime
        :returns: ZenHubConnection
        """
        factory = ZenPBClientFactory()
        service = ClientService(
            self.__endpoint,
            factory,
            retryPolicy=backoffPolicy(initialDelay=0.5, factor=3.0),
            clock=clock,
        )
        service.startService()
        return ZenHubConnection(self.__log, clock, service)
