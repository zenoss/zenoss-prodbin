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

import Globals

from Products.ZenEvents.EventServer import EventServer
from Products.ZenEvents.MailProcessor import POPProcessor

from twisted.mail.pop3client import POP3Client
from twisted.internet import reactor, protocol, defer, error

import logging
log = logging.getLogger("zen.pop3")


class POPProtocol(POP3Client):
    ''' protocol that is responsible for conversing with a pop server
    after a connection has been established.  downloads messages (and
    deletes them by default), and passes the messages back up to the
    factory to process (and turn into events)'''

    allowInsecureLogin = True
    timeout = 15

    def serverGreeting(self, unused):
        log.info('server greeting received.')
        log.info('logging in...')

        login = self.login(self.factory.user, self.factory.passwd)
        login.addCallback(self._loggedIn)
        login.addErrback(self.factory.deferred.errback)
 

    def _loggedIn(self, unused):
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
        return deferreds.addCallback(self.scanComplete)


    def _gotMessageLines(self, messageLines):
        log.info('passing message up to factory')
        self.factory.handleMessage("\r\n".join(messageLines))


    def _delete(self, unused):
        deleters = []
        if not self.factory.nodelete:
            for index in range(len(self.sizes)):
                log.info('deleting message  #%d...' % index)
                d = self.delete(index)
                deleters.append(d)

        deferreds = defer.DeferredList(deleters)
        return deferreds
    
    
    def scanComplete(self, unused):
        log.info("scan complete")
        self.quit()
    
    
class POPFactory(protocol.ClientFactory):
    """ factory that stores the configuration the protocol uses to do it's
    job."""
    
    protocol = POPProtocol

    def __init__(self, user, passwd, processor, nodelete):
        self.user = user
        self.passwd = passwd
        self.processor = processor
        self.deferred = defer.Deferred()
        self.nodelete = nodelete


    def handleMessage(self, messageData):
        self.processor.process(messageData)


    def clientConnectionFailed(self, unused, reason):
        self.deferred.errback(reason)


class ZenPOP3(EventServer):
    name = 'zenpop3'

    def __init__(self):
        EventServer.__init__(self)

        self.changeUser()
        self.processor = POPProcessor(self,self.options.eventseverity)
        
        log.info("credentials user: %s; pass: %s" % (self.options.popuser, 
            len(self.options.poppass) * '*'))
            
        self.makeFactory()
   
   
    def makeFactory(self):
        self.factory = POPFactory(self.options.popuser, self.options.poppass, 
            self.processor, self.options.nodelete)
        self.factory.deferred.addErrback(self.handleError)


    def connected(self):
        self.checkForMessages()
    

    def checkForMessages(self):
        reactor.callLater(self.options.cycletime, self.checkForMessages)
        if self.options.usessl:
            log.info("connecting to server using SSL")
            from twisted.internet.ssl import ClientContextFactory
            reactor.connectSSL(self.host, self.port, self.factory,
                ClientContextFactory())
        else:
            log.info("connecting to server using plaintext")
            reactor.connectTCP(self.options.pophost, self.options.popport,
                self.factory)
        
        self.heartbeat()


    def handleError(self, err):
        if err.type == error.TimeoutError:
            log.error("Timed out connecting to %s:%d",
                self.options.pophost, self.options.popport)
        elif err.type == error.ConnectionRefusedError:
            log.error("Connection refused by %s:%d",
                self.options.pophost, self.options.popport)
        elif err.type == error.ConnectError:
            log.error("Connection failed to %s:%d",
                self.options.pophost, self.options.popport)
        else:
            log.error(err.getErrorMessage())
            self.stop()
        
        self.makeFactory()


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
                               type="int",
                               default=60,
                               help="Frequency (in secs) to poll POP server")
        self.parser.add_option('--eventseverity',
                               dest='eventseverity', 
                               default="2",
                               type="int",
                               help="Severity for events created")



if __name__ == '__main__':
    ZenPOP3().run()

