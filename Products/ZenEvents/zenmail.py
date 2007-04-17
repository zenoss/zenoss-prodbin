#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2007 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zenmail

Turn email messages into events.

$Id$
'''

from EventServer import EventServer

from twisted.mail.pop3client import POP3Client
from twisted.internet import reactor, protocol, defer, task
from twisted.internet.ssl import ClientContextFactory
from zope.interface import implements

from MessageProcessing import MessageProcessor

import logging
log = logging.getLogger("zen.mail")


class POPProtocol(POP3Client):

    allowInsecureLogin = True
    timeout = 15


    def serverGreeting(self, greeting):
        log.info('server greeting received.')
        POP3Client.serverGreeting(self, greeting)

        log.info('logging in...')
        login = self.login(self.factory.user, self.factory.passwd)
        login.addCallback(self._loggedIn)
        login.addErrback(self._loggedIn)

        login.chainDeferred(self.factory.deferred)


    def _loggedIn(self, result):
        log.info('logged in')
        self.retrieveAndParse()


    def retrieveAndParse(self):
        d = self.listSize()
        d.addCallback(self._gotMessageSizes)

        return d


    def _gotMessageSizes(self, sizes):
        log.info('messages to retrieve: %d' % len(sizes))

        retreivers = []
        for i in range(len(sizes)):
            log.info('retrieving message #%d...' % i)
            d = self.retrieve(i)
            d.addCallback(self._gotMessageLines)
            retreivers.append(d)

        return defer.DeferredList(retreivers).addCallback(self._finished)


    def _gotMessageLines(self, messageLines):
        log.info('passing message up to factory')
        self.factory.handleMessage("\r\n".join(messageLines))


    def _finished(self, downloadResults):
        reactor.callLater(self.factory.cycletime, self.retrieveAndParse)

    
    
class POPFactory(protocol.ClientFactory):
    protocol = POPProtocol

    def __init__(self, user, passwd, processor, cycletime):
        self.user = user
        self.passwd = passwd
        self.processor = processor
        self.cycletime = cycletime
        self.deferred = defer.Deferred()


    def handleMessage(self, messageData):
        self.processor.process(messageData)


    def clientConnectionFailed(self, connection, reason):
        self.deferred.errback(reason)


class ZenMail(EventServer):
    name = 'zenmail'

    def __init__(self):
        EventServer.__init__(self)

        self.changeUser()
        self.processor = MessageProcessor(self.dmd.ZenEventManager)
        host = self.options.pophost
        port = self.options.popport
        popuser = self.options.popuser
        poppasswd = self.options.poppass
        usessl = self.options.usessl
        cycletime = self.options.cycletime

        log.info("creating POPFactory.")
        log.info("credentials user: %s; pass: %s" % (popuser, len(poppasswd) * '*'))
        self.factory = POPFactory(popuser, poppasswd, self.processor, cycletime)

        log.info("connecting to pop server: %s:%s" % (host, port))
        self.factory.deferred.addErrback(self.handleError)
        
        if usessl:
            log.info("connecting to server using SSL")
            reactor.connectSSL(host, port, self.factory, ClientContextFactory())
        else:
            log.info("connceting to server using plaintext")
            reactor.connectTCP(host, port, self.factor)


    def handleError(self, error):
        log.error(error)
        log.error(error.getErrorMessage())


    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--usessl',
                               dest='usessl',
                               default=0,
                               type="int",
                               help="Use SSL when connecting to POP server")
        self.parser.add_option('--cycletime',
                               dest='cycletime',
                               default="60",
                               type="int",
                               help="Number of seconds between polls")
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
                               default="popuser",
                               help="POP user to auth using")
        self.parser.add_option('--poppass',
                               dest='poppass', 
                               default="poppass",
                               help="POP password to auth using")



if __name__ == '__main__':
    ZenMail().main()

