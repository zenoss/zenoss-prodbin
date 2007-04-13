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

import logging
log = logging.getLogger("zen.ZenTcpClient")

from twisted.internet import reactor, protocol, defer
from Products.ZenEvents.ZenEventClasses import Status_IpService

from socket import getfqdn
hostname = getfqdn()

# this is needed to do the setUnjellyableForClass
from Products.ZenHub.services.StatusConfig import ServiceConfig

class ZenTcpTest(protocol.Protocol):

    def connectionMade(self):
        log.debug("connect to: %s" % self.transport.getPeer().host)
        sendString = self.factory.cfg.sendString
        if sendString:
            log.debug("sending: %s" % sendString)
            self.transport.write(sendString)
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

    def __init__(self, svc, status):
        self.cfg = svc
        self.deferred = defer.Deferred()
        self.status = status

    def expect(self, data):
        import re
        if self.cfg.expectRegex and not re.search(self.cfg.expectRegex, data):
            self.msg = "bad return expected:'%s' received:'%s'" % (
                        self.cfg.expectRegex, data)
        log.debug(self.msg)


    def clientConnectionLost(self, connector, reason):
        log.debug("lost: %s", reason.getErrorMessage())
        self.deferred.callback(self)
        self.deferred = None


    def clientConnectionFailed(self, connector, reason):
        log.debug("failed: %s", reason.getErrorMessage())
        log.debug(reason.type)
        self.msg = "ip service '%s' is down" % self.cfg.component
        self.deferred.callback(self)
        self.deferred = None


    def getEvent(self):
        if self.msg == "pass" and self.status > 0:
            sev = 0
            self.msg = "device:%s service:%s back up" % (
                        self.cfg.device, self.cfg.component)
            log.info(self.msg)
        elif self.msg != "pass":
            sev = self.cfg.failSeverity
            log.warn("device:%s service:%s down", 
                     self.cfg.device, self.cfg.component)
        else:
            return None
        return dict(device=self.cfg.device, 
                    component=self.cfg.component, 
                    ipAddress=self.cfg.ip, 
                    summary=self.msg, 
                    severity=sev,
                    eventClass=Status_IpService,
                    eventGroup="TCPTest", 
                    agent="ZenStatus", 
                    manager=hostname)

    def start(self):
        reactor.connectTCP(self.cfg.ip, self.cfg.port, self, self.cfg.timeout)
        return self.deferred
