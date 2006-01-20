import sys
import time
import socket 
import select
import os
import logging
import Queue
from SocketServer import UDPServer

import Globals

from Products.ZenUtils.ZeoPoolBase import  ZeoPoolBase
from Products.ZenUtils.Utils import basicAuthUrl

from Event import Event, EventHeartbeat
from SyslogProcessingThread import SyslogProcessingThread

from ZenEventClasses import AppStart, AppStop

SYSLOG_PORT = socket.getservbyname('syslog', 'udp')

class ZenSyslog(UDPServer, ZeoPoolBase):


    def __init__(self, addr='', port=SYSLOG_PORT):
        UDPServer.__init__(self, (addr, port), None)
        ZeoPoolBase.__init__(self)
        self.minpriority = self.options.minpriority
        self.phost = self.options.parsehost
        self.maxthreads = self.options.maxthreads
        self.zempath = os.path.join(self.options.dmdpath, "ZenEventManager")
        self.evtcount=0L
        self.rcptqueue = Queue.Queue()
        self._lastheartbeat = 0
        self._threadlist = []
        self._hostmap = {}       # client address/name mapping

        for i in range(self.maxthreads):
            spt = SyslogProcessingThread(self.rcptqueue, self.getZem(), 
                     self.options.minpriority, self.options.parsehost)
            self._threadlist.append(spt)
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
            socket.getfqdn(), "zenmon/zensyslog", self.options.heartbeat*3)
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStart, 
                        summary="zensyslog collector started",
                        severity=0, component="zenmon/zensyslog"))
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
                self.sendHeartbeat()
                if self.options.stats and last+5<time.time():
                    self.log.info("count=%d pool=%d, queue=%d", 
                                self.evtcount, self.available(), 
                                self.rcptqueue.qsize())
                    last = time.time()
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected exception")
        self.log.info("stopped")


    def stop(self):
        self.log.info("stopping...")
        map(lambda t: t.stop(), self._threadlist)
        map(lambda t: t.join(2), self._threadlist)
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStop, 
                        summary="zensyslog collector stopped",
                        severity=4, component="zenmon/zensyslog"))
        self.running = False


    def sendHeartbeat(self):
        if self._lastheartbeat + self.options.heartbeat < time.time():
            self.sendEvent(self.evtheartbeat)
            self._lastheartbeat = time.time()


    def sendEvent(self, evt):
        zem = None
        try:
            zem = self.getZem()
            zem.sendEvent(evt)
        finally:
            if zem: 
                zem._p_jar.close()
                del zem


    def getZem(self):
        """Return our ZenEventManager based on zempath option.
        """
        return self.getConnection(self.zempath)


    def buildOptions(self):
        ZeoPoolBase.buildOptions(self)
        self.parser.add_option('--dmdpath',
            dest='dmdpath', default="/zport/dmd",
            help="zope path to our dmd /zport/dmd")
        self.parser.add_option('--parsehost',
            dest='parsehost', action="store_true", 
            help="try to parse the hostname part of a syslog HEADER")
        self.parser.add_option('--stats',
            dest='stats', action="store_true", 
            help="print stats to log every 2 secs")
        self.parser.add_option('--logorig',
            dest='logorig', action="store_true", 
            help="log the original message")
        self.parser.add_option('--debug',
            dest='debug', action="store_true", 
            help="debug mode no threads")
        self.parser.add_option('--minpriority',
            dest='minpriority', default=6, type="int",
            help="Minimum priority that syslog will accecpt")
        self.parser.add_option('--maxthreads',
            dest='maxthreads', default=1, type="int",
            help="Max processing threads")
        self.parser.add_option('--heartbeat',
            dest='heartbeat', default=60,
            help="Number of seconds between heartbeats")


                

if __name__ == '__main__':
    ZenSyslog().serve()
