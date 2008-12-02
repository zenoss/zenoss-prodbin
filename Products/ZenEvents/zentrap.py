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

__doc__='''zentrap

Creates events from SNMP Traps.

'''

import time
import sys
import socket

import Globals

from EventServer import EventServer

from pynetsnmp import netsnmp, twistedsnmp

from twisted.internet import defer
from Products.ZenUtils.Driver import drive

# Magical interfacing with C code
import ctypes as c

# This is what struct sockaddr_in {} looks like
family = [('family', c.c_ushort)]
if sys.platform == 'darwin':
    family = [('len', c.c_ubyte), ('family', c.c_ubyte)]

class sockaddr_in(c.Structure):
    _fields_ = family + [
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

# required to decode generic SNMPv1 traps
genericTrapTypes = {
    0: 'snmp_coldStart',
    1: 'snmp_warmStart',
    2: 'snmp_linkDown',
    3: 'snmp_linkUp',
    4: 'snmp_authenticationFailure',
    5: 'snmp_egpNeighorLoss',
    }

class ZenTrap(EventServer):
    'Listen for SNMP traps and turn them into events'

    name = 'zentrap'

    def __init__(self):
        EventServer.__init__(self)
        if not self.options.useFileDescriptor and self.options.trapport < 1024:
            self.openPrivilegedPort('--listen', '--proto=udp',
                '--port=%s:%d' % (self.options.listenip,
                self.options.trapport))
        self.session = netsnmp.Session()
        if self.options.useFileDescriptor is not None:
            fileno = int(self.options.useFileDescriptor)
            # open port 1162, but then dup fileno onto it
            self.session.awaitTraps('%s:1162' % self.options.listenip, fileno)
        else:
            self.session.awaitTraps('%s:%d' % (
                self.options.listenip, self.options.trapport))
        self.oidCache = {}
        self.session.callback = self.handleTrap
        twistedsnmp.updateReactor()

    def oid2name(self, oid):
        'get oid name from cache or ZenHub'
        if type(oid) == type(()):
            oid = '.'.join(map(str, oid))
        if self.oidCache.has_key(oid):
            return defer.succeed(self.oidCache[oid])
        d = self.model().callRemote('oid2name', oid)
        def cache(name):
            self.oidCache[oid] = name
            return name
        d.addCallback(cache)
        return d

    def handleTrap(self, pdu):
        ts = time.time()

        # is it a trap?
        if pdu.sessid != 0: return

        # what address did it come from?
        #   for now, we'll make the scary assumption this data is a
        #   sockaddr_in
        transport = c.cast(pdu.transport_data, c.POINTER(sockaddr_in))
        if not transport: return
        transport = transport.contents

        #   Just to make sure, check to see that it is type AF_INET
        if transport.family != socket.AF_INET: return
        # get the address out as ( host-ip, port)
        addr = [bp2ip(transport.addr),
                transport.port[0] << 8 | transport.port[1]]

        # At the end of this callback, pdu will be deleted, so copy it
        # for asynchronous processing
        dup = netsnmp.lib.snmp_clone_pdu(c.addressof(pdu))
        if not dup:
            self.log.error("could not clone PDU for asynchronous processing")
            return
        
        def cleanup(result):
            netsnmp.lib.snmp_free_pdu(dup)
            return result

        d = self.asyncHandleTrap(addr, dup.contents, ts)
        d.addBoth(cleanup)

    def asyncHandleTrap(self, addr, pdu, ts):
        def inner(driver):
            eventType = 'unknown'
            result = {}
            if pdu.version == 1:
                # SNMP v2
                variables = netsnmp.getResult(pdu)
                for oid, value in variables:
                    oid = '.'.join(map(str, oid))
                    # SNMPv2-MIB/snmpTrapOID
                    if oid == '1.3.6.1.6.3.1.1.4.1.0':
                        yield self.oid2name(value)
                        eventType = driver.next()
                    yield self.oid2name(oid)
                    result[driver.next()] = value
            elif pdu.version == 0:
                # SNMP v1
                variables = netsnmp.getResult(pdu)
                addr[0] = '.'.join(map(str, [pdu.agent_addr[i] for i in range(4)]))
                generic = pdu.trap_type
                
                # if type is generic, use the static generic name
                eventType = genericTrapTypes.get(generic)
                
                # if type is enterprise, do an oid2name lookup
                if not eventType:
                    enterprise = lp2oid(pdu.enterprise, pdu.enterprise_length)
                    oid = "%s.%s" % (enterprise, pdu.specific_type)
                    
                    # specific check for 8072 is to remain compatible with the
                    # way Zenoss was previously handling the incorrect trap
                    # OID sent by Net-SNMP agents.
                    if enterprise.startswith('1.3.6.1.4.1.8072.4'):
                        oid = "%s.0.%s" % (enterprise, pdu.specific_type)
                        
                    yield self.oid2name(oid)
                    eventType = driver.next()
                for oid, value in variables:
                    oid = '.'.join(map(str, oid))
                    yield self.oid2name(oid)
                    result[driver.next()] = value
            else:
                self.log.error("Unable to handle trap version %d", pdu.version)
                return

            summary = 'snmp trap %s' % eventType
            self.log.debug(summary)
            community = ''
            if pdu.community_len:
                community = c.string_at(pdu.community, pdu.community_len)
            result['device'] = addr[0]
            result.setdefault('component', '')
            result.setdefault('eventClassKey', eventType)
            result.setdefault('eventGroup', 'trap')
            result.setdefault('severity', 3)
            result.setdefault('summary', summary)
            result.setdefault('community', community)
            result.setdefault('firstTime', ts)
            result.setdefault('lastTime', ts)
            result.setdefault('monitor', self.options.monitor)
            self.sendEvent(result)

            # respond to INFORM requests
            if pdu.command == netsnmp.SNMP_MSG_INFORM:
                reply = netsnmp.lib.snmp_clone_pdu(c.addressof(pdu))
                if not reply:
                    self.log.error("could not clone PDU for INFORM response")
                    raise RuntimeError("Cannot respond to INFORM PDU")
                reply.contents.command = netsnmp.SNMP_MSG_RESPONSE
                reply.contents.errstat = 0
                reply.contents.errindex = 0
                sess = netsnmp.Session(peername='%s:%d' % tuple(addr),
                                       version=pdu.version)
                sess.open()
                if not netsnmp.lib.snmp_send(sess.sess, reply):
                    netsnmp.lib.snmp_sess_perror("unable to send inform PDU",
                                                 self.session.sess)
                    netsnmp.lib.snmp_free_pdu(reply)
                sess.close()
        return drive(inner)

    def buildOptions(self):
        EventServer.buildOptions(self)
        self.parser.add_option('--trapport', '-t',
            dest='trapport', type='int', default=TRAP_PORT,
            help="Listen for SNMP traps on this port rather than the default")
        self.parser.add_option('--listenip',
            dest='listenip', default='0.0.0.0',
            help="IP address to listen on. Default is 0.0.0.0")
        self.parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor',
                               type='int',
                               help=("Read from an existing connection "
                                     " rather opening a new port."),
                               default=None)


if __name__ == '__main__':
    z = ZenTrap()
    z.run()
    z.report()

