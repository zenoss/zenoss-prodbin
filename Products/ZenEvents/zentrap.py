#! /usr/bin/env python 
#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''zentrap

Creates events from SNMP Traps.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from twisted.python import threadable
threadable.init()

from Queue import Queue

import time
import socket

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

def extract(obj, path, default = None):
    parts = path.split('/')
    for p in parts:
        try:
            obj = obj[p]
        except KeyError:
            return default
    return obj


class ZenTrap(ZCmdBase, snmpprotocol.SNMPProtocol):
    'Listen for SNMP traps and turn them into events'

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.

    def __init__(self):
        ZCmdBase.__init__(self, keeproot=True)
        snmpprotocol.SNMPProtocol.__init__(self, self.options.trapport)
        
        reactor.listenUDP(self.port, self)
        self.zem = self.dmd.ZenEventManager
        self.sendEvent(Event(device=socket.getfqdn(), 
                               eventClass=AppStart, 
                               summary="zentrap started",
                               severity=0,
                               component="zentrap"))
        self.q = Queue()
        self.log.info("started")
        #self.heartbeat()

    def handleTrap(self, data, addr):
        'Traps are processed asynchronously in a thread'
        self.q.put( (data, addr, time.time()) )

    def _findDevice(self, addr):
        'Find a device by its IP address'
        device = None
        ipObject = findIpAddress(self.dmd, addr[0])
        if ipObject:
            device = ipObject.device()
        if not device:
            device = self.dmd.Devices.findDevice(addr[0])
        return addr

    def _oid2name(self, oid):
        'short hand to get names from oids'
        return self.dmd.Mibs.oid2name(oid)
  
    def oid2name(self, oid):
        "get oids, even if we're handed slightly wrong values"
        oid = oid.lstrip('.')
        name = self._oid2name(oid)
        if not name:
            name = self._oid2name('.'.join(oid.split('.')[:-1]))
        if not name:
            return oid
        return name

    def run(self):
        'method to process traps in a thread'
        while 1:
            self.syncdb()
            args = self.q.get()
            if args is None: break
            if isinstance(args, Event):
                self.syncdb()
                self.sendEvent(args)
            else:
                self.doHandleTrap(*args)

    def doHandleTrap(self, data, addr, ts):
        eventType = 'unknown'
        result = {}
        if data['version'].get() == 1:
            # SNMP v2
            pdu = data['pdu']
            bindings = extract(data, 'pdu/snmpV2_trap/variable_bindings', [])
            bindings = extract(data, 'pdu/inform_request/variable_bindings',
                               bindings)
            for binding in bindings:
                oid = grind(binding['name'])
                value = grind(binding['value'])
                # SNMPv2-MIB/snmpTrapOID
                if oid.lstrip('.') == '1.3.6.1.6.3.1.1.4.1.0':
                    eventType = self.oid2name(value)
                result[self.oid2name(oid)] = value
        else:
            # SNMP v1
            addr = grind(extract(data, 'pdu/trap/agent_addr')), addr[1]
            enterprise = grind(extract(data, 'pdu/trap/enterprise'))
            eventType = self.oid2name(enterprise)
            generic = grind(extract(data, 'pdu/trap/generic_trap'))
            specific = grind(extract(data, 'pdu/trap/specific_trap'))
            eventType = { 0 : 'snmp_coldStart',
                          1 : 'snmp_warmStart',
                          2 : 'snmp_linkDown',
                          3 : 'snmp_linkUp',
                          4 : 'snmp_authenticationFailure',
                          5 : 'snmp_egpNeighorLoss',
                          6 : self.oid2name('%s.0.%d' % (enterprise, specific))
                          }.get(generic, eventType + "_%d" % specific)
            for binding in extract(data, 'pdu/trap/variable_bindings'):
                oid = grind(binding['name'])
                value = grind(binding['value'])
                result[self.oid2name(oid)] = value

        summary = 'snmp trap %s from %s' % (eventType, addr[0])
        self.log.debug(summary)
        ev = Event(rcvtime=ts,
                   ipAddress=addr[0],
                   severity=3,
                   device=self._findDevice(addr[0]),
                   component='',
                   agent='zentrap',
                   eventGroup='trap',
                   eventClassKey=eventType,
                   summary=summary,
                   **result)
        self.sendEvent(ev)

        diff = time.time() - ts
        self.totalTime += diff
        self.totalEvents += 1
        self.maxTime = max(diff, self.maxTime)

        if data['pdu'].has_key('inform_request'):
            r = snmpprotocol.v2c.Response()
            extract(r, 'pdu/response/request_id').set(
                extract(data, 'pdu/inform_request/request_id').get())
            r['community'].set(data['community'].get())
            reactor.callFromThread(self.informResponse, r.berEncode(), addr)


    def informResponse(self, data, addr):
        self.transport.socket.sendto(data, addr)


    def sendEvent(self, evt):
        "wrapper for sending an event"
        self.zem.sendEvent(evt)


    def heartbeat(self):
        """Since we don't do anything on a regular basis, just
        push heartbeats regularly"""
        seconds = 10
        evt = EventHeartbeat(socket.getfqdn(), "zentrap", 3*seconds)
        self.q.put(evt)
        reactor.callLater(seconds, self.heartbeat)

        
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

    def report(self):
        'report some simple diagnostics at shutdown'
        self.log.info("%d events processed in %.2f seconds",
                   self.totalEvents,
                   self.totalTime)
        if self.totalEvents > 0:
            self.log.info("%.5f average seconds per event",
                       (self.totalTime / self.totalEvents))
            self.log.info("Maximum processing time for one event was %.5f",
                          self.maxTime)

    def finish(self):
        'things to do at shutdown: thread cleanup, logs and events'
        self.q.put(None)
        self.report()
        self.sendEvent(Event(device=socket.getfqdn(), 
                             eventClass=AppStop, 
                             summary="zentrap stopped",
                             severity=4,
                             component="zentrap"))

if __name__ == '__main__':
    z = ZenTrap()
    reactor.callInThread(z.run)
    reactor.addSystemEventTrigger('before', 'shutdown', z.finish)
    reactor.run(installSignalHandlers=False)
