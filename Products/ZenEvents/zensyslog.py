#! /usr/bin/env python
# -*- coding: utf-8 -*-
# ##########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
# ##########################################################################

__doc__ = """zensyslog

Turn syslog messages into events.

"""

import time
import socket

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.python import failure
from twisted.internet import defer

import Globals
from Products.ZenEvents.EventServer import EventServer
from Products.ZenEvents.SyslogProcessing import SyslogProcessor

from Products.ZenUtils.Utils import zenPath
from Products.ZenUtils.IpUtil import asyncNameLookup
from Products.ZenUtils.Driver import drive

SYSLOG_PORT = 514
try:
    SYSLOG_PORT = socket.getservbyname('syslog', 'udp')
except socket.error:
    pass


class ZenSyslog(DatagramProtocol, EventServer):
    """
    ZenSyslog
    """

    name = 'zensyslog'
    SYSLOG_DATE_FORMAT = '%b %d %H:%M:%S'
    SAMPLE_DATE = 'Apr 10 15:19:22'

    def __init__(self):
        EventServer.__init__(self)
        if not self.options.useFileDescriptor\
             and self.options.syslogport < 1024:
            self.openPrivilegedPort('--listen', '--proto=udp',
                                    '--port=%s:%d'
                                     % (self.options.listenip,
                                    self.options.syslogport))
        self.changeUser()
        self.minpriority = self.options.minpriority
        self.processor = None

        if self.options.logorig:
            import logging
            self.olog = logging.getLogger('origsyslog')
            self.olog.setLevel(20)
            self.olog.propagate = False
            lname = zenPath('log/origsyslog.log')
            hdlr = logging.FileHandler(lname)
            hdlr.setFormatter(logging.Formatter('%(message)s'))
            self.olog.addHandler(hdlr)
        if self.options.useFileDescriptor is not None:
            self.useUdpFileDescriptor(int(self.options.useFileDescriptor))
        else:
            reactor.listenUDP(self.options.syslogport, self,
                              interface=self.options.listenip)


    def configure(self):
        """
        Initialize the daemon
        
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        def inner(driver):
            """
            Generator function to gather zProperites and then initialize.
            
            @param driver: driver
            @type driver: string
            @return: Twisted deferred object
            @rtype: Twisted deferred object
            """
            yield EventServer.configure(self)
            driver.next()
            self.log.info('Fetching the default syslog priority')
            yield self.model().callRemote('getDefaultPriority')
            self.processor = SyslogProcessor(self.sendEvent,
                    self.options.minpriority, self.options.parsehost,
                    self.options.monitor, driver.next())
            self.log.info('Configuration finished')

        return drive(inner)


    def expand(self, msg, client_address):
        """
        Expands a syslog message into a string format suitable for writing
        to the filesystem such that it appears the same as it would
        had the message been logged by the syslog daemon.
        
        @param msg: syslog message
        @type msg: string
        @param client_address: IP info of the remote device (ipaddr, port)
        @type client_address: tuple of (string, number)
        @return: message
        @rtype: string
        """
        # pri := facility * severity
        stop = msg.find('>')

        # check for a datestamp.  default to right now if date not present
        start = stop + 1
        stop = start + len(ZenSyslog.SAMPLE_DATE)
        dateField = msg[start:stop]
        try:
            date = time.strptime(dateField,
                                 ZenSyslog.SYSLOG_DATE_FORMAT)
            year = time.localtime()[0]
            date = (year, ) + date[1:]
            start = stop + 1
        except ValueError:

        # date not present, so use today's date
            date = time.localtime()

        # check for a hostname.  default to localhost if not present
        stop = msg.find(' ', start)
        if msg[stop - 1] == ':':
            hostname = client_address[0]
        else:
            hostname = msg[start:stop]
            start = stop + 1

        # the message content
        body = msg[start:]

        # assemble the message
        prettyTime = time.strftime(ZenSyslog.SYSLOG_DATE_FORMAT, date)
        message = '%s %s %s' % (prettyTime, hostname, body)
        return message


    def datagramReceived(self, msg, client_address):
        """
        Consume the network packet
        
        @param msg: syslog message
        @type msg: string
        @param client_address: IP info of the remote device (ipaddr, port)
        @type client_address: tuple of (string, number)
        """
        (ipaddr, port) = client_address
        if self.options.logorig:
            if self.options.logformat == 'human':
                message = self.expand(msg, client_address)
            else:
                message = msg
            self.olog.info(message)

        if self.options.noreverseLookup:
            d = defer.succeed(ipaddr)
        else:
            d = asyncNameLookup(ipaddr)
        d.addBoth(self.gotHostname, (msg, ipaddr, time.time()))


    def gotHostname(self, response, data):
        """
        Send the resolved address, if possible, and the event via the thread
        
        @param response: Twisted response
        @type response: Twisted response
        @param data: (msg, ipaddr, rtime)
        @type data: tuple of (string, string, datetime object)
        """
        (msg, ipaddr, rtime) = data
        host = ipaddr
        self.log.debug( "Response = %s" % response )
        if not isinstance(response, failure.Failure):
            host = response
        if self.processor:
            self.processor.process(msg, ipaddr, host, rtime)


    def buildOptions(self):
        """
        Command-line options
        """
        EventServer.buildOptions(self)
        self.parser.add_option('--dmdpath', dest='dmdpath',
                               default='/zport/dmd',
                               help='Zope path to our DMD /zport/dmd')
        self.parser.add_option('--parsehost', dest='parsehost',
                               action='store_true', default=False,
                               help='Try to parse the hostname part of a syslog HEADER'
                               )
        self.parser.add_option('--stats', dest='stats',
                               action='store_true', default=False,
                               help='Print statistics to log every 2 secs')
        self.parser.add_option('--logorig', dest='logorig',
                               action='store_true', default=False,
                               help='Log the original message')
        self.parser.add_option('--logformat', dest='logformat',
                               default='human',
                               help='Human-readable (/var/log/messages) or raw (wire)'
                               )
        self.parser.add_option('--minpriority', dest='minpriority',
                               default=6, type='int',
                               help='Minimum priority message that zensyslog will accept'
                               )
        self.parser.add_option('--heartbeat', dest='heartbeat',
                               default=60,
                               help='Number of seconds between heartbeats'
                               )
        self.parser.add_option('--syslogport', dest='syslogport',
                               default=SYSLOG_PORT, type='int',
                               help='Port number to use for syslog events'
                               )
        self.parser.add_option('--listenip', dest='listenip',
                               default='0.0.0.0',
                               help='IP address to listen on. Default is 0.0.0.0'
                               )
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor', type='int',
                               help='Read from an existing connection rather opening a new port.'
                               , default=None)
        self.parser.add_option('--noreverseLookup', dest='noreverseLookup',
                               action='store_true', default=False,
                               help="Don't convert the remote device's IP address to a hostname."
                               )


if __name__ == '__main__':
    zsl = ZenSyslog()
    zsl.run()
    zsl.report()

