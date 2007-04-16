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

from EventServer import EventServer
from Event import Event, EventHeartbeat

from ZenEventClasses import Status_Snmp
from Products.ZenModel.IpAddress import findIpAddress

from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol
from twistedsnmp import snmpprotocol

TRAP_PORT = 162
try:
    TRAP_PORT = socket.getservbyname('snmptrap', 'udp')
except socket.error:
    pass

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


class ZenTrap(EventServer, snmpprotocol.SNMPProtocol):
    'Listen for SNMP traps and turn them into events'

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.

    name = 'zentrap'

    def __init__(self):
        EventServer.__init__(self)
        snmpprotocol.SNMPProtocol.__init__(self, self.options.trapport)
        reactor.listenUDP(self.port, self)


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
        try:
            return socket.gethostbyaddr(addr[0])[0]
        except socket.herror:
            pass
        return addr[0]

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

    def doHandleRequest(self, data, addr, ts):
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
                          6 : self.oid2name('%s' % (enterprise,))
                          }.get(generic, eventType + "_%d" % specific)
            for binding in extract(data, 'pdu/trap/variable_bindings'):
                oid = grind(binding['name'])
                value = grind(binding['value'])
                result[self.oid2name(oid)] = value

        device = self._findDevice(addr)
        summary = 'snmp trap %s from %s' % (eventType, device)
        self.log.debug(summary)
        community = data['community'].get()
        result.setdefault('agent', 'zentrap')
        result.setdefault('component', '')
        result.setdefault('device', device)
        result.setdefault('eventClassKey', eventType)
        result.setdefault('eventGroup', 'trap')
        result.setdefault('rcvtime', ts)
        result.setdefault('severity', 3)
        result.setdefault('summary', summary)
        result.setdefault('community', community)
        result['ipAddress'] = addr[0]
        self.sendEvent(result)

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


    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--trapport', '-t',
                               dest='trapport', type='int', default=TRAP_PORT)


if __name__ == '__main__':
    z = ZenTrap()
    z.main()
