import sys, string, time, socket, re, os
import logging
logging.basicConfig()


from SocketServer import UDPServer

import Globals

from Products.ZenUtils.ZeoPoolBase import  ZeoPoolBase
from Event import Event
from SyslogProcessingThread import SyslogProcessingThread
from MySqlSendEvent import MySqlSendEventThread

SYSLOG_PORT = socket.getservbyname('syslog', 'udp')

class Syslogd(UDPServer, ZeoPoolBase):

    def __init__(self, addr='', port=SYSLOG_PORT):
        UDPServer.__init__(self, (addr, port), None)
        ZeoPoolBase.__init__(self)
        self.minpriority = self.options.minpriority
        self._hostmap = {}       # client address/name mapping
        self.log.info("syslog start")
        self.statusEvt = Event(device=socket.getfqdn(), 
                                eventClass="SyslogStatus", 
                                summary="syslog collector started",
                                severity=0, component="syslog")
        self.heartbeat = Event(device=socket.getfqdn(), component="zensyslog")
        app = self.getConnection()
        zem = self.getZem(app)
        self.senderThread = MySqlSendEventThread(zem)
        app._p_jar.close()
        del app, zem
        if not self.options.debug:
            self._evqueue = self.senderThread.getqueue()
            self.senderThread.start()
        self.sendEvent(self.statusEvt)
        

    def sendEvent(self, evt):
        if self.options.debug:
            self.senderThread.sendEvent(evt)
        else:
            self._evqueue.put(evt)


    def getZem(self, app):
        """Return our ZenEventManager based on zempath option.
        """
        return app.unrestrictedTraverse(self.options.zempath)


    def getEventClass(self, app):
        """Return our ZenEventManager based on zempath option.
        """
        return app.unrestrictedTraverse(self.options.eventclasspath)


    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        ipaddress = client_address[0]
        hostname = self.resolvaddr(ipaddress)
        msg = request[0]
        spt = SyslogProcessingThread(self,request[0],ipaddress,hostname)
        if not self.options.debug: spt.start() 
   
    
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
        self.running = 1
        while self.running:
            self.handle_request()


    def sigTerm(self, signum, frame):
        self.running = 0
        if os.path.exists(self.pidfile):
            self.log.info("delete pidfile %s", self.pidfile)
            os.remove(self.pidfile)
        self.log.info('Daemon %s shutting down' % self.__class__.__name__)
        self.statusEvt.summary = "syslog collector stopped"
        self.sendEvent(self.statusEvt)
        self.senderThread.stop()


    def buildOptions(self):
        ZeoPoolBase.buildOptions(self)
        self.parser.add_option('--zempath',
            dest='zempath', default="/zport/dmd/ZenEventManager",
            help="zope path to our ZenEventManager /zport/dmd/ZenEventManager")
        self.parser.add_option('--eventclasstpath',
            dest='eventclasspath', default="/zport/dmd/EventClasses",
            help="zope path to our EventClasses /zport/dmd/EventClasses")
        self.parser.add_option('--debug',
            dest='debug', action="store_true", 
            help="debug mode no threads")
        self.parser.add_option('--minpriority',
            dest='minpriority', default=6,
            help="Minimum priority that syslog will accecpt")


                

if __name__ == '__main__':
    Syslogd().serve()
