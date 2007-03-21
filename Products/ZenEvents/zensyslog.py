#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

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
        reactor.listenUDP(self.options.syslogport, self)


    def datagramReceived(self, msg, client_address):
        """Use a separate thread to process the request."""
        ipaddr, port = client_address
        if self.options.logorig: 
            self.olog.info(msg)
        lookupPointer(host,timeout=(1,)).addBoth(self.gotHostname, (msg,ipaddr,time.time()) )


    def gotHostname(self, host, data):
        "send the resolved address, if possible, and the event via the thread"
        if isinstance(host, failure.Failure):
            host = data[1]
        self.q.put( (host,) + data )


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


if __name__ == '__main__':
    ZenSyslog().main()
