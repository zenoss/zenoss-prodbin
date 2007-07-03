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
#! /usr/bin/env python 
# Notes: database wants events in UTC time
# Events page shows local time, as determined on the server where zenoss runs

__doc__='''zenpop3

Turn email messages into events.

$Id$
'''

from EventServer import EventServer

from twisted.mail.pop3client import POP3Client
from twisted.internet import reactor, protocol, defer, task
from twisted.internet.ssl import ClientContextFactory
from zope.interface import implements
from Products.ZenRRD.RRDDaemon import RRDDaemon
from Products.ZenUtils.Driver import drive, driveLater


from MessageProcessing import MessageProcessor

import logging
log = logging.getLogger("zen.pop3")


class POPProtocol(POP3Client):
    ''' protocol that is responsible for conversing with a pop server
    after a connection has been established.  downloads messages (and
    deletes them by default), and passes the messages back up to the
    factory to process (and turn into events)'''

    allowInsecureLogin = True
    timeout = 15

    def serverGreeting(self, greeting):
        log.info('server greeting received.')
        log.info('logging in...')

        login = self.login(self.factory.user, self.factory.passwd)
        login.addCallback(self._loggedIn)
        login.addErrback(self.factory.deferred.errback)
 

    def _loggedIn(self, result):
        log.info('logged in')
        return self.retrieveAndParse()


    def retrieveAndParse(self):
        d = self.listSize()
        d.addCallback(self._gotMessageSizes)

        return d


    def _gotMessageSizes(self, sizes):
        log.info('messages to retrieve: %d' % len(sizes))

        self.sizes = sizes

        retreivers = []
        for i in range(len(sizes)):
            log.info('retrieving message #%d...' % i)
            d = self.retrieve(i)
            d.addCallback(self._gotMessageLines)
            retreivers.append(d)

        deferreds = defer.DeferredList(retreivers) 
        deferreds.addCallback(self._delete)

        if self.factory.cycle:
            return deferreds.addCallback(self._finished)
        else:
            return deferreds.addCallback(self.factory.scanComplete)


    def _gotMessageLines(self, messageLines):
        log.info('passing message up to factory')
        self.factory.handleMessage("\r\n".join(messageLines))


    def _delete(self, results):
        if not self.factory.nodelete:
            deleters = []
            for index in range(len(self.sizes)):
                log.info('deleting message  #%d...' % index)
                d = self.delete(index)
                deleters.append(d)

        deferreds = defer.DeferredList(deleters)
        return deferreds


    def _finished(self, downloadResults):
        log.info('sleeping for %d seconds.' % self.factory.cycletime)
        reactor.callLater(self.factory.cycletime, self.retrieveAndParse)

    
    
class POPFactory(protocol.ClientFactory):
    ''' factory that stores the configuration the protocol uses to do it's
    job.'''
    
    protocol = POPProtocol

    def __init__(self, user, passwd, 
                 processor, cycletime, cycle, nodelete, finish):
        self.user = user
        self.passwd = passwd
        self.processor = processor
        self.cycletime = cycletime
        self.cycle = cycle
        self.deferred = defer.Deferred()
        self.nodelete = nodelete
        self.finish = finish


    def handleMessage(self, messageData):
        self.processor.process(messageData)


    def clientConnectionFailed(self, connection, reason):
        self.deferred.errback(reason)


    def scanComplete(self, results):
        log.info("scan complete")
        self.finish()


class ZenPOP3(EventServer, RRDDaemon):
    name = 'zenpop3'

    def __init__(self):
        EventServer.__init__(self)
        RRDDaemon.__init__(self, ZenPOP3.name)

        self.changeUser()
        self.processor = MessageProcessor(self.dmd.ZenEventManager)
        host = self.options.pophost
        port = self.options.popport
        popuser = self.options.popuser
        poppasswd = self.options.poppass
        usessl = self.options.usessl
        cycletime = int(self.options.cycletime)
        cycle = int(self.options.cycle)
        nodelete = int(self.options.nodelete)

        log.info("credentials user: %s; pass: %s" % (popuser, 
                                                     len(poppasswd) * '*'))
        self.factory = POPFactory(popuser, poppasswd, 
                                  self.processor, cycletime, cycle, nodelete,
                                  self._finish)
        log.info("connecting to pop server: %s:%s" % (host, port))
        self.factory.deferred.addErrback(self.handleError)
        
        if usessl:
            log.info("connecting to server using SSL")
            reactor.connectSSL(host, port, self.factory, ClientContextFactory())
        else:
            log.info("connceting to server using plaintext")
            reactor.connectTCP(host, port, self.factory)


    def handleError(self, error):
        log.error(error)
        log.error(error.getErrorMessage())

        self.finish()


    def _finish(self):
        self.finish()


    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--usessl',
                               dest='usessl',
                               default=False,
                               action="store_true",
                               help="Use SSL when connecting to POP server")
        self.parser.add_option('--nodelete',
                               dest='nodelete',
                               default=False,
                               action="store_true",
                               help="Leave messages on POP server")
        self.parser.add_option('--pophost',
                               dest='pophost', 
                               default="pop.zenoss.com",
                               help="POP server to auth against")
        self.parser.add_option('--popport',
                               dest='popport', 
                               default="110",
                               type="int",
                               help="POP port to auth against")
        self.parser.add_option('--popuser',
                               dest='popuser', 
                               default="zenoss",
                               help="POP user to auth using")
        self.parser.add_option('--poppass',
                               dest='poppass', 
                               default="zenoss",
                               help="POP password to auth using")
        self.parser.add_option('--cycletime',
                               dest='cycletime',
                               default=60,
                               help="Frequency (in secs) to poll POP server")



if __name__ == '__main__':
    ZenPOP3().main()

