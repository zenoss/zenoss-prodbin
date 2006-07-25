#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
"""
Error types:

1. timeout (no connection)
2. connection refused - port not available on remote end
3. bad value - value returned did not match expectRegex

"""

import sys
import re
import socket
import logging
log = logging.getLogger("zen.ZenTcpClient")

from twisted.internet import reactor, protocol, defer
from Products.ZenEvents.Event import Event

hostname = socket.getfqdn()

class ZenTcpTest(protocol.Protocol):

    def connectionMade(self):
        log.debug("connect to: %s" % self.transport.getPeer().host)
        if self.factory.sendString:
            log.debug("sending: %s" % self.factory.sendString)
            self.transport.write(self.factory.sendString)
            reactor.callLater(self.factory.timeout,
                              self.transport.loseConnection)
        else:
            self.transport.loseConnection()

    def dataReceived(self, data):
        log.debug("data: %s", data)
        self.factory.expect(data)
        self.transport.loseConnection()

        
class ZenTcpClient(protocol.ClientFactory):
    protocol = ZenTcpTest
    msg = "pass"

    def __init__(self, svc):
        self.svc = svc
        self.ip = svc.getManageIp()
        self.port = svc.getPort()
        self.sendString = svc.getSendString()
        self.expectRegex = svc.getExpectRegex()
        self.timeout=15
        self.deferred = defer.Deferred()


    def expect(self, data):
        if self.expectRegex and not re.search(self.expectRegex, data):
            self.msg = "bad return expected:'%s' received:'%s'" % (
                        self.expectRegex, data)
        log.debug(self.msg)


    def clientConnectionLost(self, connector, reason):
        log.debug("lost: %s", reason.getErrorMessage())
        evt = self.mkevent()
        self.deferred.callback((self.svc.key(), evt))


    def clientConnectionFailed(self, connector, reason):
        log.debug("failed: %s", reason.getErrorMessage())
        log.debug(reason.type)
        self.msg = "ip service '%s' is down" % self.svc.name()
        evt = self.mkevent()
        self.deferred.callback((self.svc.key(), evt))


    def mkevent(self):
        if self.msg == "pass" and self.svc.getStatus() > 0:
            sev = 0
            log.info("device:%s service:%s back up", 
                     self.svc.hostname(), self.svc.name())
        elif self.msg != "pass":
            sev = self.svc.getFailSeverity()
            log.warn("device:%s service:%s down", 
                     self.svc.hostname(), self.svc.name())
        else:
            return None
        return Event(
                device=self.svc.hostname(), 
                component=self.svc.name(), 
                ipAddress=self.ip, 
                summary=self.msg, 
                severity=sev,
                eventClass="/Status/IpService",
                eventGroup="TCPTest", 
                agent="ZenTCP", 
                manager=hostname)

    

def test(svc):
    """Pass a Service object and return a deferred that will call back
    with results of service test.
    """
    client = ZenTcpClient(svc)
    reactor.connectTCP(client.ip, client.port, client, client.timeout)
    return client.deferred
