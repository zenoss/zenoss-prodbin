import sys
import time
import socket 
import select
import os
import logging
import xmlrpclib
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
        self.zempath = os.path.join(self.options.dmdpath, "ZenEventManager")
        self.processThreads = {}
        self._lastheartbeat = 0
        self._hostmap = {}       # client address/name mapping
        self.evtheartbeat = EventHeartbeat(
            socket.getfqdn(), "zenmon/zensyslog", self.options.heartbeat*3)
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStop, 
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
        self._hostmap[clientip] = host   #GIL protected shared write
        return host


    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        ipaddress = client_address[0]
        hostname = self.resolvaddr(ipaddress)
        msg = request[0]
        spt = SyslogProcessingThread(self,request[0],ipaddress, hostname,
                                    self.options.parsehost)
        if not self.options.debug: 
            spt.start() 
   
        
    def handle_request(self):
        """Handle one request, and don't block"""
        res = select.select([self.socket,],[],[],1)
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
        while self.running:
            try:
                self.handle_request()
                self.sendHeartbeat()
            except (SystemExit, KeyboardInterrupt): raise
            except:
                self.log.exception("unexpected exception")
        self.log.info("stopped")


    def stop(self):
        self.log.info("stopping...")
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStop, 
                        summary="zensyslog collector stopped",
                        severity=2, component="zensyslog"))
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
            if zem: zem._p_jar.close()

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
        self.parser.add_option('--logorig',
            dest='logorig', action="store_true", 
            help="log the original message")
        self.parser.add_option('--debug',
            dest='debug', action="store_true", 
            help="debug mode no threads")
        self.parser.add_option('--minpriority',
            dest='minpriority', default=6,
            help="Minimum priority that syslog will accecpt")
        self.parser.add_option('--heartbeat',
            dest='heartbeat', default=60,
            help="Number of seconds between heartbeats")


                

if __name__ == '__main__':
    ZenSyslog().serve()
