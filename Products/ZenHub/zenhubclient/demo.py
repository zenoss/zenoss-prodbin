#! /usr/bin/env python

import logging
import md5

from twisted.cred.credentials import UsernamePassword
from twisted.internet.endpoints import clientFromString
from twisted.internet import defer, reactor
from twisted.spread import pb

import Globals  # noqa: F401

from Products.ZenHub import PB_PORT
from Products.ZenHub.zenhubclient.client import ZenHubClient

TIMEOUT = 30.0

calls = (
    (md5.new().hexdigest(), t)
    for t in range(30, 1, -1)
)


class App(pb.Referenceable):
    """
    """

    def __init__(self, reactor):
        self.__reactor = reactor

        # Configure/initialize the ZenHub client
        self.creds = UsernamePassword(
            "admin", "zenoss",
        )
        self.endpointDescriptor = "tcp:{host}:{port}".format(
            host="localhost", port=PB_PORT,
        )
        self.endpoint = clientFromString(reactor, self.endpointDescriptor)
        self.__client = None

    @defer.inlineCallbacks
    def run(self):
        log = logging.getLogger("zen.zhc.App")
        try:
            log.info("Waiting for ZenHub connection")
            client = yield ZenHubClient.connect(
                reactor, self.endpoint, self.creds, self, TIMEOUT,
            )
            log.info("Received zenhub client %s", client)
            self.__reactor.addSystemEventTrigger(
                'before', 'shutdown', client.stop,
            )
            log.info("Asking for remote service")
            svc = yield client.getService(
                "Products.ZenHub.services.echo:DelayedEchoService",
                "localhost",
            )
            log.info("Received remote service %s", svc)
            dfrs = [
                svc.callRemote("echo", mesg, wait)
                for mesg, wait in calls
            ]
            result = yield defer.DeferredList(dfrs)
            # result = yield svc.callRemote("echo", "Hello", 2)
            log.info("service returned %s results", len(result))
        except Exception:
            log.exception("Failure")


def main(reactor):
    app = App(reactor)
    reactor.callLater(0, app.run)


if __name__ == "__main__":
    # for hk in logging._handlers:
    #     h = logging._handlers.get(hk)
    #     h.close()
    # ch = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # ch.setFormatter(formatter)
    logging.getLogger().handlers[0].setFormatter(formatter)
    log = logging.getLogger("zen")
    # import pdb; pdb.set_trace()
    # log.addHandler(ch)
    log.setLevel(logging.DEBUG)

    log.info("Starting App")
    reactor.callWhenRunning(main, reactor)
    reactor.run()
