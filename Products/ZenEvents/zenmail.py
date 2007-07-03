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

__doc__='''zenmail

Turn email messages into events.

$Id$
'''

from EventServer import EventServer

from twisted.mail import smtp
from twisted.internet import reactor, protocol, defer
from zope.interface import implements
from Products.ZenRRD.RRDDaemon import RRDDaemon

from email.Header import Header

from MessageProcessing import MessageProcessor

import logging
log = logging.getLogger("zen.mail")


class MessageWriter(object):
    implements(smtp.IMessage)

    def __init__(self):
        self.lines = []


    def lineReceived(self, line):
        self.lines.append(line)


    def eomReceived(self):
        log.info('message data completed.')
        self.lines.append('')
        messageData = '\n'.join(self.lines)

        if True:
            return defer.succeed(None)
        else: 
            return defer.failure(None)


    def connectionLost(self):
        log.info('connection lost unexpectedly')
        del(self.lines)


class ZenossDelivery(object):
    implements(smtp.IMessageDelivery)

    def __init__(self):
        pass


    def receivedHeader(self, helo, origin, recipients):
        myHostname, clientIP = helo
        headerValue = 'by %s from %s with ESMTP ; %s' % (
            myHostname, clientIP, smtp.rfc822date())
        
        log.info('relayed (or sent directly) from: %s' % clientIP)
        
        header = 'Received: %s' % Header(headerValue)
        return header


    def validateTo(self, user):
        log.info('to: %s' % user.dest)
        return self.makeMessageWriter


    def makeMessageWriter(self):
        return MessageWriter()


    def validateFrom(self, helo, originAddress):
        log.info("from: %s" % originAddress)
        return originAddress
    
    
class SMTPFactory(protocol.ServerFactory):
    def __init__(self):
        pass

    def buildProtocol(self, addr):
        delivery = ZenossDelivery()
        smtpProtocol = smtp.SMTP(delivery)
        smtpProtocol.factory = self
        return smtpProtocol


class ZenMail(EventServer, RRDDaemon):
    name = 'zenmail'

    def __init__(self):
        EventServer.__init__(self)
        RRDDaemon.__init__(self, ZenMail.name)

        self.changeUser()
        self.processor = MessageProcessor(self.dmd.ZenEventManager)

        self.factory = SMTPFactory()

        if self.options.useFileDescriptor != -1:
            self.useUdpFileDescriptor(int(self.options.useFileDescriptor))
        else:
            reactor.listenTCP(2525, self.factory)
            reactor.run()


    def handleError(self, error):
        log.error(error)
        log.error(error.getErrorMessage())

        self.finish()


    def _finish(self):
        self.finish()


    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor', 
                               default="-1",
                               type="int",
                               help="File descriptor to use for listening")
        self.parser.add_option('--listenPort',
                               dest='listenPort', 
                               default="2525",
                               type="int",
                               help="Alternative listen port to use")


if __name__ == '__main__':
    ZenMail().main()

