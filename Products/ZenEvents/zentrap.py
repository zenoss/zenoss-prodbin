import time
import socket 

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase

from Event import Event, EventHeartbeat

from ZenEventClasses import AppStart, AppStop
from Products.ZenEvents.Exceptions import ZenBackendFailure

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol

TRAP_PORT = socket.getservbyname('snmptrap', 'udp')

class ZenTrap(ZCmdBase, DatagramProtocol):


    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        self.zem = self.dmd.ZenEventManager
        reactor.listenUDP(self.options.trapPort, self)
        self.sendEvent(Event(device=socket.getfqdn(), 
                               eventClass=AppStart, 
                               summary="zentrap started",
                               severity=0,
                               component="zentrap"))
        self.log.info("started")


    def datagramReceived(self, data, addr):
        if self.options.rawLog:
            fp = open(self.options.rawLog, 'a')
            try:
                arg = (time.time(), addr, data)
                fp.write('%r\n' % (arg, ))
            except Exception, ex:
                self.log.error('Exception: %s' % ex)
            fp.close()
        self.log.debug('Received %r from %r', data, addr)


    def sendEvent(self, evt):
        "wrapper for sending an event"
        self.zem.sendEvent(evt)


    def heartbeat(self):
        """Since we don't do anything on a regular basis,
        just send heartbeats regularly"""
        seconds = 10
        evt = EventHeartbeat(socket.getfqdn(), "zentrap", 3*seconds)
        self.sendEvent(evt)
        reactor.callLater(self.heartbeat, seconds)

        
    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--trapPort', '-t',
                               dest='trapPort', type='int', default=TRAP_PORT)
        self.parser.add_option('--rawLog', '-l', dest='rawLog')
        
    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()

if __name__ == '__main__':
    z = ZenTrap()
    reactor.run(installSignalHandlers=False)
