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

import sys
import time
import socket 
import select
import os
import logging
import Queue
from SocketServer import UDPServer

import Globals

import transaction

from Products.ZenUtils.Utils import basicAuthUrl

from EventServer import EventServer
from Event import Event, EventHeartbeat
from SyslogProcessingThread import SyslogProcessingThread

from ZenEventClasses import AppStart, AppStop
from Products.ZenEvents.Exceptions import ZenBackendFailure

SYSLOG_PORT = socket.getservbyname('syslog', 'udp')

class ZenSyslog(UDPServer, EventServer):


    def __init__(self, addr=''):
        EventServer.__init__(self)
        UDPServer.__init__(self, (addr, self.options.syslogport), None)
        self.changeUser()
        self.minpriority = self.options.minpriority
        self.phost = self.options.parsehost
        self.zempath = os.path.join(self.options.dmdpath, "ZenEventManager")
        self.evtcount=0L
        self.rcptqueue = Queue.Queue()
        self._lastheartbeat = 0
        self._threadlist = []
        self._hostmap = {}       # client address/name mapping

        spt = SyslogProcessingThread(self.rcptqueue, self.dmd.ZenEventManager, 
                 self.options.minpriority, self.options.parsehost)
        spt.start() 

        if self.options.logorig:
            self.olog = logging.getLogger("origsyslog")
            self.olog.setLevel(20)
            self.olog.propagate = False
            lname = os.path.join(os.environ['ZENHOME'],"log","origsyslog.log")
            hdlr = logging.FileHandler(lname)
            hdlr.setFormatter(logging.Formatter("%(message)s"))
            self.olog.addHandler(hdlr)
        self.evtheartbeat = EventHeartbeat(
            socket.getfqdn(), "zensyslog", self.options.heartbeat*3)
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStart, 
                        summary="zensyslog collector started",
                        severity=0, component="zensyslog"))
        self.log.info("started")
        

    def resolvaddr(self, clientip):
        # build the client address/name mapping
        host = self._hostmap.get(clientip, False)
        if host: return host
        try:
            host = socket.gethostbyaddr(clientip)[0]
            #host = host.split('.')[0]       # keep only the host name
        except socket.error:
            host = clientip
        self._hostmap[clientip] = host   
        return host


    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        ipaddr = client_address[0]
        host = self.resolvaddr(ipaddr)
        msg = request[0]
        rtime = time.time()
        if self.options.logorig: 
            self.olog.info(msg)
        self.evtcount += 1
        self.rcptqueue.put((msg, ipaddr, host, rtime))
  

    def handle_request(self, seltimeout=1):
        """Handle one request, and don't block"""
        res = select.select([self.socket,],[],[],seltimeout)
        if not res[0]: return
        request, client_address = self.get_request()
        try:
            self.process_request(request, client_address)
        except (SystemExit, KeyboardInterrupt): raise
        except:
            self.log.exception("request from %s:%d failed" % client_address)


    def serve(self):
        "Run the service until it is stopped with the stop() method."
        self.running = True
        last = 0
        while self.running:
            try:
                seltimeout = 1
                if not self.rcptqueue.empty(): seltimeout = 0
                self.handle_request(seltimeout)
                if self.options.stats and last+60<time.time():
                    self.log.info("count=%d pool=%d, queue=%d", 
                                self.evtcount, self.available(), 
                                self.rcptqueue.qsize())
                    last = time.time()
                self.sendHeartbeat()
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected exception")
        self.log.info("stopped")


    def stop(self):
        self.log.info("stopping...")
        if hasattr(self, "_threadlist"):
            map(lambda t: t.stop(), self._threadlist)
            map(lambda t: t.join(2), self._threadlist)
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStop, 
                        summary="zensyslog collector stopped",
                        severity=4, component="zensyslog"))
        self.running = False


    def sendHeartbeat(self):
        if self._lastheartbeat + self.options.heartbeat < time.time():
            self.sendEvent(self.evtheartbeat)
            self._lastheartbeat = time.time()


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
    ZenSyslog().serve()
