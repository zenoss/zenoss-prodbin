###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
#! /usr/bin/env python 

__doc__='''zentrap

Creates events from SNMP Traps.

$Id$
'''

__version__ = "$Revision$"[11:-2]

from twisted.python import threadable
threadable.init()

import time
import socket

import Globals

from EventServer import EventServer
from Products.ZenModel.IpAddress import findIpAddress

from pynetsnmp import netsnmp, twistedsnmp

# Magical interfacing with C code
import ctypes as c

# This is what struct sockaddr_in {} looks like
class sockaddr_in(c.Structure):
    _fields_ = [
        ('family', c.c_ushort),
        ('port', c.c_ubyte * 2),        # need to decode from net-byte-order
        ('addr', c.c_ubyte * 4)
        ];

# teach python that the return type of snmp_clone_pdu is a pdu pointer
netsnmp.lib.snmp_clone_pdu.restype = netsnmp.netsnmp_pdu_p

TRAP_PORT = 162
try:
    TRAP_PORT = socket.getservbyname('snmptrap', 'udp')
except socket.error:
    pass

def lp2oid(ptr, length):
    "Convert a pointer to an array of longs to an oid"
    return '.'.join([str(ptr[i]) for i in range(length)])

def bp2ip(ptr):
    "Convert a pointer to 4 bytes to a dotted-ip-address"
    return '.'.join([str(ptr[i]) for i in range(4)])


class ZenTrap(EventServer):
    'Listen for SNMP traps and turn them into events'

    totalTime = 0.
    totalEvents = 0
    maxTime = 0.

    name = 'zentrap'

    def __init__(self):
        EventServer.__init__(self)
        self.session = netsnmp.Session()
        if self.options.useFileDescriptor is not None:
            fileno = int(self.options.useFileDescriptor)
            # open port 1162, but then dup fileno onto it
            self.session.awaitTraps('0.0.0.0:1162', fileno)
        else:
            self.session.awaitTraps('0.0.0.0:%d' % self.options.trapport)
        self.session.callback = self.handleTrap
        twistedsnmp.updateReactor()

    def handleTrap(self, pdu):
        'Traps are processed asynchronously in a thread'
        # FIXME: not using the threaded-based posting
        self.doHandleRequest(time.time(), pdu)

    def _findDevice(self, addr):
        'Find a device by its IP address'
        device = None
        ipObject = findIpAddress(self.dmd, addr[0])
        if ipObject:
            device = ipObject.device()
        if not device:
            device = self.dmd.Devices.findDevice(addr[0])
        if device:
            return device.id
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
        if type(oid) == type(()):
            oid = '.'.join(map(str, oid))
        name = self._oid2name(oid)
        if not name:
            name = self._oid2name('.'.join(oid.split('.')[:-1]))
        if not name:
            return oid
        return name

    def doHandleRequest(self, ts, pdu):
        eventType = 'unknown'
        result = {}
        # is it a trap?
        if pdu.sessid != 0: return
        # what address did it come from?
        #   for now, we'll make the scary assumption this data is a sockaddr_in
        transport = c.cast(pdu.transport_data, c.POINTER(sockaddr_in))
        if not transport: return
        transport = transport.contents
        #   Just to make sure, check to see that it is type AF_INET
        if transport.family != socket.AF_INET: return
        # get the address out as ( host-ip, port)
        addr = (bp2ip(transport.addr),
                transport.port[0] << 8 | transport.port[1])
        if pdu.version == 1:
            # SNMP v2
            variables = netsnmp.getResult(pdu)
            for oid, value in variables:
                oid = '.'.join(map(str, oid))
                # SNMPv2-MIB/snmpTrapOID
                if oid == '1.3.6.1.6.3.1.1.4.1.0':
                    eventType = self.oid2name(value)
                result[self.oid2name(oid)] = value
        elif pdu.version == 0:
            # SNMP v1
            variables = netsnmp.getResult(pdu)
            addr = ('.'.join(map(str, [pdu.agent_addr[i] for i in range(4)])),
                    addr[1])
            enterprise = lp2oid(pdu.enterprise, pdu.enterprise_length)
            eventType = self.oid2name(enterprise)
            generic = pdu.trap_type
            specific = pdu.specific_type
            eventType = { 0 : 'snmp_coldStart',
                          1 : 'snmp_warmStart',
                          2 : 'snmp_linkDown',
                          3 : 'snmp_linkUp',
                          4 : 'snmp_authenticationFailure',
                          5 : 'snmp_egpNeighorLoss',
                          6 : self.oid2name('%s.0.%d' % (enterprise, specific))
                          }.get(generic, eventType + "_%d" % specific)
            for oid, value in variables:
                oid = '.'.join(map(str, oid))
                result[self.oid2name(oid)] = value
        else:
            self.log.error("Unable to handle trap version %d", pdu.version)
            return

        device = self._findDevice(addr)
        summary = 'snmp trap %s from %s' % (eventType, device)
        self.log.debug(summary)
        community = c.string_at(pdu.community, pdu.community_len)
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

        # respond to INFORM requests
        if pdu.command == netsnmp.SNMP_MSG_INFORM:
            reply = netsnmp.lib.snmp_clone_pdu(c.addressof(pdu))
            if not reply:
                self.log.error("could not clone PDU for INFORM response")
                raise SnmpError("Cannot respond to INFORM PDU")
            reply.contents.command = netsnmp.SNMP_MSG_RESPONSE
            reply.contents.errstat = 0
            reply.contents.errindex = 0
            sess = netsnmp.Session(peername='%s:%d' % addr,
                                   version=pdu.version)
            sess.open()
            if not netsnmp.lib.snmp_send(sess.sess, reply):
                netsnmp.lib.snmp_sess_perror("unable to send inform PDU", self.session.sess)
                netsnmp.lib.snmp_free_pdu(reply)
            sess.close()

    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--trapport', '-t',
                               help=('Listen for SNMP traps on this '
                                     'port rather than the default'),
                               dest='trapport', type='int', default=TRAP_PORT)
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor',
                               type='int',
                               help=("Read from an existing connection "
                                     " rather opening a new port."),
                               default=None)


if __name__ == '__main__':
    z = ZenTrap()
    z.main()
