###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, 2009 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
__doc__ = """ZenTcpClient
Connect to the remote service and (optionally) test the output from
the service against what we expect.

Error types:

    1. timeout (no connection)
    2. connection refused - port not available on remote end
    3. bad value - value returned did not match expectRegex

"""
import re
import logging
log = logging.getLogger("zen.ZenTcpClient")
from socket import getfqdn
hostname = getfqdn()

from twisted.internet import reactor, protocol, defer
from Products.ZenEvents.ZenEventClasses import Status_IpService
from Products.ZenUtils.Utils import unused


# needed for pb/jelly
from Products.ZenHub.services.StatusConfig import ServiceConfig
unused(ServiceConfig)

class ZenTcpTest(protocol.Protocol):
    """
    Twisted class to make a TCP/IP connection to a remote IP service
    and report back the result.
    """
    defer = None
    data = ""

    def connectionMade(self):
        """
        Connected successfully to the remote device, now test against any
        regex that we might have and record the result.
        """
        log.debug("Connected to %s" % self.transport.getPeer().host)
        self.factory.msg = "pass"
        self.cfg = self.factory.cfg

        if self.cfg.sendString:
            for line in self.cfg.sendString.split('\n'):
                log.debug("Sending: %s" % line)
                self.transport.write(line + '\n')

        if self.cfg.expectRegex:
            log.debug("Waiting for results to check against regex '%s'" % (
                      self.cfg.expectRegex ))
            self.defer = reactor.callLater(self.cfg.timeout, self.expectTimeout)
        else:
            self.loseConnection()


    def dataReceived(self, data):
        """
        Compare the data from the remote device to what we expect in the
        regex.

        @parameter data: output from remote service
        @type data: string
        """
        log.debug("%s %s received data: %s" % (self.cfg.device,
                  self.cfg.component, data))
        self.data += data
        if self.cfg.expectRegex:
            if re.search(self.cfg.expectRegex, data):
                log.debug("Found %s in '%s' -- closing connection" % (
                          self.cfg.expectRegex, data))
                self.loseConnection()
            else:
                log.debug("No match for %s in '%s' -- looking for more data" % (
                          self.cfg.expectRegex, data))


    def expectTimeout(self):
        """
        Called if we timeout waiting for the service to connect or for
        receiving a response from the service that matches our regex.
        """
        msg = "IP Service %s TIMEOUT waiting for '%s'" % (
                    self.cfg.component, self.cfg.expectRegex)
        log.debug( "%s %s" % (self.cfg.ip, msg) )
        self.factory.msg = msg
        self.loseConnection()


    def loseConnection(self):
        """
        Shut down the connection and cleanup.
        """
        ip, port = self.transport.addr
        log.debug("Closed connection to %s on port %s for %s" % (
                  ip, port, self.cfg.component))
        self.data = ""
        try:
            self.defer.cancel()
        except:
            self.defer = None
        self.transport.loseConnection()



class ZenTcpClient(protocol.ClientFactory):
    """
    Client class to run TCP tests.
    """
    protocol = ZenTcpTest
    msg = "pass"
    deferred = None

    def __init__(self, svc, status):
        self.cfg = svc
        self.status = status

    def clientConnectionLost(self, connector, reason):
        """
        Record why the connection to the remote device was dropped.

        @parameter connector: Twisted protocol object
        @type connector: Twisted protocol object
        @parameter reason: explanation for the connection loss
        @type reason: Twisted error object
        """
        unused(connector)
        log.debug("Lost connection to %s (%s) port %s : %s" % (
                  self.cfg.device, self.cfg.ip, self.cfg.port,
                  reason.getErrorMessage() ))
        if self.deferred:
            self.deferred.callback(self)
        self.deferred = None


    def clientConnectionFailed(self, connector, reason):
        """
        Record why the connection to the remote device failed.

        @parameter connector: Twisted protocol object
        @type connector: Twisted protocol object
        @parameter reason: explanation for the connection loss
        @type reason: Twisted error object
        """
        unused(connector)
        log.debug("Connection to %s (%s) port %s  failed: %s" % (
                  self.cfg.device, self.cfg.ip, self.cfg.port,
                  reason.getErrorMessage() ))
        log.debug(reason.type)
        self.msg = "IP Service %s is down" % self.cfg.component
        if self.deferred:
            self.deferred.callback(self)
        self.deferred = None


    def getEvent(self):
        """
        Called by zenstatus to report status information about a service.

        @return: event of what happened to our service test
        @rtype: dictionary
        """
        log.debug("status:%s msg:%s", self.status, self.msg)
        if self.msg == "pass" and self.status > 0:
            self.status = sev = 0
            self.msg = "IP Service %s back up" % self.cfg.component
            log.info(self.msg)

        elif self.msg != "pass":
            self.status += 1
            sev = self.cfg.failSeverity
            log.warn(self.msg)

        else:
            # Don't send an event as there's no problem and
            # nothing to clear.
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
        """
        Called by zenstatus to make a connection attempt to the service.

        @return: Twisted deferred
        @rtype: Twisted deferred
        """
        d = self.deferred = defer.Deferred()
        reactor.connectTCP(self.cfg.ip, self.cfg.port, self, self.cfg.timeout)
        return d
