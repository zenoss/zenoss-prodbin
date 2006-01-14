import sys
import time
import socket 
import os
import logging

from SocketServer import UDPServer

import Globals

from Products.ZenUtils.ZeoPoolBase import  ZeoPoolBase
from Event import Event
from SyslogProcessingThread import SyslogProcessingThread
from MySqlSendEvent import MySqlSendEventThread

from ZenEventClasses import AppStart, AppStop

SYSLOG_PORT = socket.getservbyname('syslog', 'udp')

class ZenSyslog(UDPServer, ZeoPoolBase):

    def __init__(self, addr='', port=SYSLOG_PORT):
        UDPServer.__init__(self, (addr, port), None)
        ZeoPoolBase.__init__(self)
        self.minpriority = self.options.minpriority
        self.processThreads = {}
        self._hostmap = {}       # client address/name mapping
        app = self.getConnection()
        zempath = os.path.join(self.options.dmdpath, "ZenEventManager")
        zem = app.unrestrictedTraverse(zempath)
        self.eventThread = MySqlSendEventThread(zem)
        app._p_jar.close()
        del app, zem
        if not self.options.debug:
            self.eventThread.start()
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStart, 
                        summary="zensyslog collector started",
                        severity=0, component="zensyslog"))
        self.log.info("started")
        

    def sendEvent(self, evt):
        self.eventThread.sendEvent(evt)


    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        ipaddress = client_address[0]
        hostname = self.resolvaddr(ipaddress)
        msg = request[0]
        spt = SyslogProcessingThread(self,request[0],ipaddress, hostname,
                                    self.options.parsehost)
        if not self.options.debug: 
            spt.start() 
   
   
        
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


    def serve(self):
        "Run the service until it is stopped with the stop() method."
        self.running = True
        while self.running:
            self.handle_request()
        self.log.info("stopped")


    def stop(self):
        self.log.info("stopping...")
        self.sendEvent(Event(device=socket.getfqdn(), 
                        eventClass=AppStop,
                        summary="zensyslog collector stopped",
                        severity=2, component="zensyslog"))
        self.eventThread.stop()
        self.running = False


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


                

if __name__ == '__main__':
    ZenSyslog().serve()
