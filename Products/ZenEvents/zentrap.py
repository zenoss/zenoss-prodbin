
import time
import socket 
import os
import glob

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase

from Event import Event, EventHeartbeat

from ZenEventClasses import AppStart, AppStop, SnmpStatus
from Products.ZenEvents.Exceptions import ZenBackendFailure
from Products.ZenModel.IpAddress import findIpAddress

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twistedsnmp import snmpprotocol

TRAP_PORT = socket.getservbyname('snmptrap', 'udp')

SMI_MIB_DIR = os.path.join(os.environ['ZENHOME'], 'share/mibs')
MIBS = glob.glob(SMI_MIB_DIR + '/*/*-MIB*')
#MIBS = glob.glob(SMI_MIB_DIR + '/*/NETSCREE*')
#MIBS.extend(glob.glob(SMI_MIB_DIR + '/*/SNMPv2-MIB*'))

def grind(obj):
    '''Chase an object down to its value.

    Example: getting a timeticks value:

       ticks = obj['value']['application_syntax']['timeticks_value'].get()

    becomes:

       ticks = grind(obj)

    '''
    if hasattr(obj, 'keys'):
        return grind(obj.values()[0])
    return obj.get()

Oids = {}

def oid2name(oid):
    oid = oid.lstrip('.')
    name = Oids.get(oid, None)
    if name:
        return name
    name = Oids.get('.'.join(oid.split('.')[:-1]), None)
    if name:
        return name
    return oid

class ZenTrap(ZCmdBase, snmpprotocol.SNMPProtocol):


    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        snmpprotocol.SNMPProtocol.__init__(self, self.options.trapport)
        self.work = []
        self.log.debug("loading mibs")
        for m in MIBS:
            result = {}
            self.log.debug("%s", m.split('/')[-1])
            try:
                exec os.popen('smidump -fpython %s 2>/dev/null' % m) in result
                mib = result.get('MIB', None)
                if mib:
                    for name, values in mib['nodes'].items():
                        Oids[values['oid']] = name
            except Exception, ex:
                self.log.warning("Unable to load mib %s", m)
        self.log.debug("Loaded %d oid names", len(Oids))
        
        reactor.listenUDP(self.port, self)
        self.zem = self.dmd.ZenEventManager
        self.sendEvent(Event(device=socket.getfqdn(), 
                               eventClass=AppStart, 
                               summary="zentrap started",
                               severity=0,
                               component="zentrap"))
        self.log.info("started")

    def handleTrap(self, data, addr):
        self.work.insert(0, (data, addr, time.time()) )
        reactor.callLater(0, self.doHandleTrap)

    def _findDevice(self, addr):
        device = None
        ipObject = findIpAddress(self.dmd, addr[0])
        if ipObject:
            device = ipObject.device()
        if not device:
            device = self.dmd.Devices.findDevice(addr[0])
        return device

    def doHandleTrap(self):
        if not self.work: return
        data, addr, ts = self.work.pop()
        # self.log.debug('Received %r from %r, %d more work', data, addr, len(self.work))
        device = self._findDevice(addr)

        eventType = 'unknown'
        result = {}
        if data['version'].get() == 1:
            for binding in data['pdu']['snmpV2_trap']['variable_bindings']:
                oid = grind(binding['name'])
                value = grind(binding['value'])
                # SNMPv2-MIB/snmpTrapOID
                if oid.lstrip('.') == '1.3.6.1.6.3.1.1.4.1.0':
                    eventType = oid2name(value)
                result[oid2name(oid)] = value

        else:
            addr = grind(data['pdu']['trap']['agent_addr']), addr[1]
            
            eventType = oid2name(grind(data['pdu']['trap']['enterprise']))
            device = self._findDevice(addr)
            for binding in data['pdu']['trap']['variable_bindings']:
                oid = grind(binding['name'])
                value = grind(binding['value'])
                result[oid2name(oid)] = value

        if device:
            ev = Event(rcvtime=ts,
                       ipAddress = addr[0],
                       device = device.id,
                       severity = 3,
                       eventClass = '%s' % eventType,
                       summary = 'snmp trap %s from %s' % (eventType, addr[0]),
                       **result)
            self.sendEvent(ev)

        if not device:
            self.log.warning("Trap for unknown IP address (%s): %s" %
                             (addr[0], result))
        reactor.callLater(0, self.doHandleTrap)


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
        self.parser.add_option('--trapport', '-t',
                               dest='trapport', type='int', default=TRAP_PORT)
        
    def sigTerm(self, signum, frame):
        'controlled shutdown of main loop on interrupt'
        try:
            ZCmdBase.sigTerm(self, signum, frame)
        except SystemExit:
            reactor.stop()

if __name__ == '__main__':
    z = ZenTrap()
    reactor.run(installSignalHandlers=False)
