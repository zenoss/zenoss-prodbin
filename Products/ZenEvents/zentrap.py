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

__doc__ = """zentrap

Creates events from SNMP Traps.

"""

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

# Some vendors form their trap MIBs to insert a 0 before the
# specific part of the v1 trap, but the device doesn't actually
# send the 0. Unfortunately we have to make explicit exceptions
# for these to get the OIDs decoded properly.
expandableV1Prefixes = (
    '1.3.6.1.2.1.17',        # Spanning Tree Protocol
    '1.3.6.1.4.1.1916',      # Extreme Networks
    '1.3.6.1.4.1.6247',      # Comtech
    '1.3.6.1.4.1.8072',      # Net-SNMP
    '1.3.6.1.4.1.12394.1.2', # Rainbow
    )


class ZenTrap(EventServer):
    """
    Listen for SNMP traps and turn them into events
    Connects to the EventService service in zenhub.
    """

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


    def oid2name(self, oid, exactMatch=True, strip=False):
        """
        Get OID name from cache or ZenHub

        @param oid: SNMP Object IDentifier
        @type oid: string
        @param exactMatch: unused
        @type exactMatch: boolean
        @param strip: unused
        @type strip: boolean
        @return Twisted deferred object
        @rtype: Twisted deferred object
        @todo: make exactMatch and strip work
        """
        if type(oid) == type(()):
            oid = '.'.join(map(str, oid))
        cacheKey = "%s:%r:%r" % (oid, exactMatch, strip)
        if self.oidCache.has_key(cacheKey):
            return defer.succeed(self.oidCache[cacheKey])

        self.log.debug("OID cache miss on %s (exactMatch=%r, strip=%r)" % (
            oid, exactMatch, strip))
        # Note: exactMatch and strip are ignored by zenhub
        d = self.model().callRemote('oid2name', oid, exactMatch, strip)

        def cache(name, key):
            """
            Twisted callback to cache and return the name

            @param name: human-readable-name form of OID
            @type name: string
            @param key: key of OID and params
            @type key: string
            @return: the name parameter
            @rtype: string
            """
            self.oidCache[key] = name
            return name

        d.addCallback(cache, cacheKey)
        return d


    def handleTrap(self, pdu):
        """
        Accept a packet from the network and spin off a Twisted
        deferred to handle the packet.

        @param pdu: raw packet
        @type pdu: binary
        """
        ts = time.time()

        # Is it a trap?
        if pdu.sessid != 0: return

        # What address did it come from?
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
            self.log.error("Could not clone PDU for asynchronous processing")
            return
        
        def cleanup(result):
            """
            Twisted callback to delete a previous memory allocation

            @param result: packet
            @type result: binary
            @return: the result parameter
            @rtype: binary
            """
            netsnmp.lib.snmp_free_pdu(dup)
            return result

        d = self.asyncHandleTrap(addr, dup.contents, ts)
        d.addBoth(cleanup)


    def asyncHandleTrap(self, addr, pdu, ts):
        """
        Twisted callback to process a trap

        @param addr: packet-sending host's IP address, port info
        @type addr: ( host-ip, port)
        @param pdu: raw packet
        @type pdu: binary
        @param ts: time stamp
        @type ts: datetime
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        def inner(driver):
            """
            Generator function that actually processes the packet

            @param driver: Twisted deferred object
            @type driver: Twisted deferred object
            @return: Twisted deferred object
            @rtype: Twisted deferred object
            """
            eventType = 'unknown'
            result = {}
            if pdu.version == 1:
                # SNMP v2
                variables = netsnmp.getResult(pdu)
                for oid, value in variables:
                    oid = '.'.join(map(str, oid))
                    # SNMPv2-MIB/snmpTrapOID
                    if oid == '1.3.6.1.6.3.1.1.4.1.0':
                        yield self.oid2name(value, exactMatch=False, strip=False)
                        eventType = driver.next()
                    else:
                        yield self.oid2name(oid, exactMatch=False, strip=True)
                        result[driver.next()] = value

            elif pdu.version == 0:
                # SNMP v1
                variables = netsnmp.getResult(pdu)
                addr[0] = '.'.join(map(str, [pdu.agent_addr[i] for i in range(4)]))
                enterprise = lp2oid(pdu.enterprise, pdu.enterprise_length)
                yield self.oid2name(enterprise, exactMatch=False, strip=False)
                eventType = driver.next()
                generic = pdu.trap_type
                specific = pdu.specific_type
                oid = "%s.%d" % (enterprise, specific)
                for oidPrefix in expandableV1Prefixes:
                    if enterprise.startswith(oidPrefix):
                        oid = "%s.0.%d" % (enterprise, specific)
                                
                yield self.oid2name(oid, exactMatch=False, strip=False)
                eventType = { 0 : 'snmp_coldStart',
                              1 : 'snmp_warmStart',
                              2 : 'snmp_linkDown',
                              3 : 'snmp_linkUp',
                              4 : 'snmp_authenticationFailure',
                              5 : 'snmp_egpNeighorLoss',
                              6 : driver.next()
                              }.get(generic, eventType + "_%d" % specific)
                for oid, value in variables:
                    oid = '.'.join(map(str, oid))
                    yield self.oid2name(oid, exactMatch=False, strip=True)
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
                    self.log.error("Could not clone PDU for INFORM response")
                    raise RuntimeError("Cannot respond to INFORM PDU")
                reply.contents.command = netsnmp.SNMP_MSG_RESPONSE
                reply.contents.errstat = 0
                reply.contents.errindex = 0
                sess = netsnmp.Session(peername='%s:%d' % tuple(addr),
                                       version=pdu.version)
                sess.open()
                if not netsnmp.lib.snmp_send(sess.sess, reply):
                    netsnmp.lib.snmp_sess_perror("Unable to send inform PDU",
                                                 self.session.sess)
                    netsnmp.lib.snmp_free_pdu(reply)
                sess.close()
        return drive(inner)


    def buildOptions(self):
        """
        Command-line options to be supported
        """
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
                                     " rather than opening a new port."),
                               default=None)


if __name__ == '__main__':
    z = ZenTrap()
    z.run()
    z.report()

