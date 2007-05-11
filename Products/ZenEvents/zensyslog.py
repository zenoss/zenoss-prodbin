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

__doc__='''zensyslog

Turn syslog messages into events.

$Id$
'''

import time
import socket 
import os

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.names.client import lookupPointer
from twisted.python import failure

from EventServer import EventServer
from SyslogProcessing import SyslogProcessor

SYSLOG_PORT = 514
try:
    SYSLOG_PORT = socket.getservbyname('syslog', 'udp')
except socket.error:
    pass

class ZenSyslog(DatagramProtocol, EventServer):

    name = 'zensyslog'
    SYSLOG_DATE_FORMAT = '%b %d %H:%M:%S'
    SAMPLE_DATE = 'Apr 10 15:19:22'


    def __init__(self):
        EventServer.__init__(self)
        self.changeUser()
        self.minpriority = self.options.minpriority
        self.processor = SyslogProcessor(self.dmd.ZenEventManager, 
                                         self.options.minpriority,
                                         self.options.parsehost)

        if self.options.logorig:
            import logging
            self.olog = logging.getLogger("origsyslog")
            self.olog.setLevel(20)
            self.olog.propagate = False
            lname = os.path.join(os.environ['ZENHOME'],"log","origsyslog.log")
            hdlr = logging.FileHandler(lname)
            hdlr.setFormatter(logging.Formatter("%(message)s"))
            self.olog.addHandler(hdlr)
        if self.options.useFileDescriptor is not None:
            self.useUdpFileDescriptor(int(self.options.useFileDescriptor))
        else:
            reactor.listenUDP(self.options.syslogport, self)


    def expand(self, msg, client_address):
        """expands a syslog message into a string format suitable for writing
        to the filesystem such that it appears the same as it would
        had the message been logged by the syslog daemon."""
        
        # pri := facility * severity
        stop = msg.find('>')
        pri = msg[1:stop]
        
        # check for a datestamp.  default to right now if date not present
        start = stop + 1
        stop = start + len(ZenSyslog.SAMPLE_DATE)
        dateField = msg[start:stop]
        try:
            date = time.strptime(dateField, ZenSyslog.SYSLOG_DATE_FORMAT)
            year = time.localtime()[0]
            date = (year,) + date[1:]
            start = stop + 1
        except  ValueError:
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
        """Use a separate thread to process the request."""
        ipaddr, port = client_address
        if self.options.logorig:
            if self.options.logformat == 'human':
                message = self.expand(msg, client_address)
            else:
                message = msg

            self.olog.info(message)

        ptr = '.'.join(ipaddr.split('.')[::-1]) + '.in-addr.arpa'
        lookupPointer(ptr, timeout=(1,)).addBoth(self.gotHostname, (msg,ipaddr,time.time()))


    def gotHostname(self, response, data):
        "send the resolved address, if possible, and the event via the thread"
        if isinstance(response, failure.Failure):
            self.q.put( (data[1],) + data )
        else:
            self.q.put( (str(response[0][0].payload.name),) + data )


    def doHandleRequest(self, host, msg, ipaddr, rtime):
        "process a single syslog message, called from the inherited thread"
        self.processor.process(msg, ipaddr, host, rtime)


    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--dmdpath',
            dest='dmdpath', default="/zport/dmd",
            help="zope path to our dmd /zport/dmd")
        self.parser.add_option('--parsehost',
            dest='parsehost', action="store_true",  default=False,
            help="try to parse the hostname part of a syslog HEADER")
        self.parser.add_option('--stats',
            dest='stats', action="store_true",  default=False,
            help="print stats to log every 2 secs")
        self.parser.add_option('--logorig',
            dest='logorig', action="store_true",  default=False,
            help="log the original message")
        self.parser.add_option('--logformat',
            dest='logformat', default="human",
            help="human (/var/log/messages) or raw (wire)")
        self.parser.add_option('--debug',
            dest='debug', action="store_true",  default=False,
            help="debug mode no threads")
        self.parser.add_option('--minpriority',
            dest='minpriority', default=6, type="int",
            help="Minimum priority that syslog will accecpt")
        self.parser.add_option('--heartbeat',
            dest='heartbeat', default=60,
            help="Number of seconds between heartbeats")
        self.parser.add_option('--syslogport',
            dest='syslogport', default=SYSLOG_PORT, type='int',
            help="Port number to use for syslog events")
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor',
                               type='int',
                               default=None)


if __name__ == '__main__':
    ZenSyslog().main()
