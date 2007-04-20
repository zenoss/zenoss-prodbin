###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import logging

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet.error import ConnectBindError

log = logging.getLogger("zen.Portscanner")

class ScanProtocol(Protocol):

    def connectionMade(self):
        self.factory.deferred.callback("success")
        self.transport.loseConnection()

class ScanFactory(ClientFactory):

    protocol = ScanProtocol

    def __init__(self):
        self.deferred = defer.Deferred()

    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)
        self.deferred = None

    def clientConnectionLost(self, connector, reason):
        pass

class ReconnectingScanFactory(ReconnectingClientFactory):

    protocol = ScanProtocol

    def __init__(self):
        self.deferred = defer.Deferred()

    def clientConnectionFailed(self, connector, reason):
        self.deferred.errback(reason)
        if reason.type == ConnectBindError:
            self.connector = connector
            self.retry()

class Scanner(object):
    '''
    '''
    def __init__(self, hosts, portRange=(1, 10000), portList=[], 
        queueCount=50, timeout=30):
        if isinstance(hosts, list):
            self.hosts = hosts
        else:
            self.hosts = [hosts]
        self.portRange = (portRange[0], portRange[1] + 1)
        self.portList = portList
        self.queueCount = queueCount
        self.timeout = timeout
        self.data = {
            'success': {},
            'failure': {},
        }

    def prepare(self):
        '''
        The use of DeferredSemaphore() here allows us to control the
        number of deferreds (and therefore connections) created at once,
        thus providing a way for systems to use the script efficiently.
        '''

        dl = []
        semaphore = defer.DeferredSemaphore(self.queueCount)
        if self.portList:
            ports = portList
        else:
            ports = range(*self.portRange)
        for host in self.hosts:
            for port in ports:
                d = semaphore.run(self.doFactory, host, port)
                dl.append(d)
        dl = defer.DeferredList(dl, consumeErrors=True)
        return dl

    def run(self):
        d = self.prepare()
        d.addCallback(self.finishRun)
        reactor.run()

    def doFactory(self, host, port):
        factory = ScanFactory()
        reactor.connectTCP(host, port, factory, timeout=self.timeout)
        d = factory.deferred
        d.addCallback(self.recordConnection, host, port)
        d.addErrback(self.recordFailure, host, port)
        return d

    def recordConnection(self, result, host, port):
        hostData = self.data['success'].setdefault(host, [])
        log.debug('Connected to %s:%d' % (host, port))
        hostData.append(port)

    def recordFailure(self, failure, host, port):
        hostData = self.data['failure'].setdefault(host, [])
        data = (port, failure.getErrorMessage())
        log.debug('Failed to connect to %s:%d -- %s' (host, port, data[1]))
        hostData.append(data)

    def finishRun(self, result=None):
        reactor.stop()
        self.printResults()

    def printResults(self):
        print "Open Ports:"
        for host, ports in self.getSuccesses().items():
            print "Host: %s" % host
            for port in ports:
                print "\topen port: %i" % port
        errors = {}
        for host, portAndError in self.getFailures().items():
            for port, error in portAndError:
                errors.setdefault(error, 0)
                errors[error] += 1
        print "\nErrors encountered, and their counts:"
        for error, count in errors.items():
            print "\t%s -- %i" % (error, count)

    def getSuccesses(self):
        return self.data['success']

    def getFailures(self):
        return self.data['failure']

