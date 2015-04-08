##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2011-2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__ = """zentrap

Creates events from SNMP Traps.
Currently a wrapper around the Net-SNMP C library.
"""

import time
import sys
import socket
import errno
import base64
import logging
import os.path
from collections import defaultdict
from struct import unpack
from ipaddr import IPAddress

log = logging.getLogger("zen.zentrap")

# Magical interfacing with C code
import ctypes as c

import Globals
import zope.interface
import zope.component
from zope.interface import implements

from twisted.python.failure import Failure
from twisted.internet import defer

from Products.ZenHub.interfaces import ICollectorEventTransformer, \
                                       TRANSFORM_CONTINUE, \
                                       TRANSFORM_DROP

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollector, ICollectorPreferences,\
                                             IEventService, \
                                             IScheduledTask, IStatisticsService
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SimpleTaskSplitter,\
                                        BaseTask, TaskStates
from Products.ZenUtils.observable import ObservableMixin


from pynetsnmp import netsnmp, twistedsnmp

from Products.ZenUtils.captureReplay import CaptureReplay
from Products.ZenEvents.EventServer import Stats
from Products.ZenUtils.Utils import unused
from Products.ZenUtils.Utils import unused, zenPath
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenHub.services.SnmpTrapConfig import User
unused(Globals, DeviceProxy, User)

from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_WARNING


# This is what struct sockaddr_in {} looks like
family = [('family', c.c_ushort)]
if sys.platform == 'darwin':
    family = [('len', c.c_ubyte), ('family', c.c_ubyte)]

class sockaddr_in(c.Structure):
    _fields_ = family + [
        ('port', c.c_ubyte * 2),     # need to decode from net-byte-order
        ('addr', c.c_ubyte * 4),
        ]

class sockaddr_in6(c.Structure):
    _fields_ = family + [
        ('port', c.c_ushort),        # need to decode from net-byte-order
        ('flow', c.c_ubyte * 4),
        ('addr', c.c_ubyte * 16),
        ('scope_id', c.c_ubyte * 4),
        ]

_pre_parse_factory = c.CFUNCTYPE(c.c_int,
                                 c.POINTER(netsnmp.netsnmp_session),
                                 c.POINTER(netsnmp.netsnmp_transport),
                                 c.c_void_p,
                                 c.c_int)

# teach python that the return type of snmp_clone_pdu is a pdu pointer
netsnmp.lib.snmp_clone_pdu.restype = netsnmp.netsnmp_pdu_p

# Version codes from the PDU
SNMPv1 = 0
SNMPv2 = 1
SNMPv3 = 3

class FakePacket(object):
    """
    A fake object to make packet replaying feasible.
    """
    def __init__(self):
        self.fake = True


class SnmpTrapPreferences(CaptureReplay):
    zope.interface.implements(ICollectorPreferences)

    def __init__(self):
        """
        Constructs a new PingCollectionPreferences instance and
        provides default values for needed attributes.
        """
        self.collectorName = 'zentrap'
        self.configCycleInterval = 20 # minutes
        self.cycleInterval = 5 * 60 # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.SnmpTrapConfig'

        # Will be filled in based on buildOptions
        self.options = None

        self.configCycleInterval = 20*60
        self.task = None

    def postStartupTasks(self):
        self.task = TrapTask('zentrap', configId='zentrap')
        yield self.task

    def buildOptions(self, parser):
        """
        Command-line options to be supported
        """
        TRAP_PORT = 162
        try:
            TRAP_PORT = socket.getservbyname('snmptrap', 'udp')
        except socket.error:
            pass
        parser.add_option('--trapport', '-t',
            dest='trapport', type='int', default=TRAP_PORT,
            help="Listen for SNMP traps on this port rather than the default")
        parser.add_option('--useFileDescriptor',
                               dest='useFileDescriptor',
                               type='int',
                               help=("Read from an existing connection "
                                     " rather than opening a new port."),
                               default=None)
        parser.add_option('--trapFilterFile',
                          dest='trapFilterFile',
                          type='string',
                          help=("File that contains trap oids to keep, should be in $ZENHOME/etc."),
                          default=None)

        self.buildCaptureReplayOptions(parser)

    def postStartup(self):
        # Ensure that we always have an oidMap
        daemon = zope.component.getUtility(ICollector)
        daemon.oidMap = {}
        # add our collector's custom statistics
        statService = zope.component.queryUtility(IStatisticsService)
        statService.addStatistic("events", "COUNTER")

def ipv6_is_enabled():
    "test if ipv6 is enabled"

    # hack for ZEN-12088 - TODO: remove next line
    return False

    try:
        socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
    except socket.error, e:
        if e.errno == errno.EAFNOSUPPORT:
            return False
        raise
    return True

class TrapTask(BaseTask, CaptureReplay):
    """
    Listen for SNMP traps and turn them into events
    Connects to the TrapService service in zenhub.
    """
    zope.interface.implements(IScheduledTask)

    def __init__(self, taskName, configId,
                 scheduleIntervalSeconds=3600, taskConfig=None):
        BaseTask.__init__(self, taskName, configId,
                 scheduleIntervalSeconds, taskConfig)
        self.log = log

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = self._daemon
        self._statService = zope.component.queryUtility(IStatisticsService)
        # For compatibility with captureReplay
        self.options = self._daemon.options

        self.oidMap = self._daemon.oidMap
        self.stats = Stats()

        # Command-line argument sanity checking
        self.processCaptureReplayOptions()
        self.session=None
        self._replayStarted = False
        if not self.options.replayFilePrefix:
            trapPort = self._preferences.options.trapport
            if not self._preferences.options.useFileDescriptor and trapPort < 1024:
                listen_ip = "ipv6" if ipv6_is_enabled() else "0.0.0.0"
                # Makes call to zensocket here (does an exec* so it never returns)
                self._daemon.openPrivilegedPort('--listen', '--proto=udp', '--port=%s:%d' % (listen_ip, trapPort))
                self.log("Unexpected return from openPrivilegedPort. Exiting.")
                sys.exit(1)

            # Start listening for SNMP traps
            self.log.info("Starting to listen on SNMP trap port %s", trapPort)
            self.session = netsnmp.Session()
            listening_protocol = "udp6" if ipv6_is_enabled() else "udp"
            if self._preferences.options.useFileDescriptor is not None:
                # open port 1162, but then dup fileno onto it
                listening_address = listening_protocol + ':1162'
                fileno = int(self._preferences.options.useFileDescriptor)
            else:
                listening_address = '%s:%d' % (listening_protocol, trapPort)
                fileno = -1
            self._pre_parse_callback = _pre_parse_factory(self._pre_parse)
            debug = self.log.isEnabledFor(logging.DEBUG)
            self.session.awaitTraps(listening_address, fileno, self._pre_parse_callback, debug)
            self.session.callback = self.receiveTrap
            twistedsnmp.updateReactor()

    def doTask(self):
        """
        This is a wait-around task since we really are called
        asynchronously.
        """
        if self.options.replayFilePrefix and not self._replayStarted:
            log.debug("Replay starting...")
            self._replayStarted=True
            self.replayAll()
            log.debug("Replay done...")
            return
        return defer.succeed("Waiting for SNMP traps...")

    def isReplaying(self):
        """
        @returns True if we are replaying a packet instead of capturing one
        """
        return len(self._preferences.options.replayFilePrefix) > 0

    def getEnterpriseString(self, pdu):
        """
        Get the enterprise string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: enterprise string
        @rtype: string
        """
        def lp2oid(ptr, length):
            "Convert a pointer to an array of longs to an OID"
            return '.'.join([str(ptr[i]) for i in range(length)])

        if hasattr(pdu, "fake"): # Replaying a packet
            enterprise = pdu.enterprise
        else:
            enterprise = lp2oid(pdu.enterprise, pdu.enterprise_length)
        return enterprise

    def getResult(self, pdu):
        """
        Get the values from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: variables from the PDU or Fake packet
        @rtype: dictionary
        """
        if hasattr(pdu, "fake"): # Replaying a packet
            variables = pdu.variables
        else:
            variables = netsnmp.getResult(pdu)
        return variables

    def getCommunity(self, pdu):
        """
        Get the community string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: SNMP community
        @rtype: string
        """
        community = ''
        if hasattr(pdu, "fake"): # Replaying a packet
            community = pdu.community
        elif pdu.community_len:
                community = c.string_at(pdu.community, pdu.community_len)

        return community

    def convertPacketToPython(self, addr, pdu):
        """
        Store the raw packet for later examination and troubleshooting.

        @param addr: packet-sending host's IP address and port
        @type addr: (string, number)
        @param pdu: raw packet
        @type pdu: binary
        @return: Python FakePacket object
        @rtype: Python FakePacket object
        """
        packet = FakePacket()
        packet.version = pdu.version
        packet.host = addr[0]
        packet.port = addr[1]
        packet.variables = netsnmp.getResult(pdu)
        packet.community = ''
        packet.enterprise_length = pdu.enterprise_length

        # Here's where we start to encounter differences between packet types
        if pdu.version == SNMPv1:
            # SNMPv1 can't be received via IPv6
            packet.agent_addr =  [pdu.agent_addr[i] for i in range(4)]
            packet.trap_type = pdu.trap_type
            packet.specific_type = pdu.specific_type
            packet.enterprise = self.getEnterpriseString(pdu)
            packet.community = self.getCommunity(pdu)

        return packet

    def replay(self, pdu):
        """
        Replay a captured packet

        @param pdu: raw packet
        @type pdu: binary
        """
        ts = time.time()
        self.asyncHandleTrap([pdu.host, pdu.port], pdu, ts)

    def oid2name(self, oid, exactMatch=True, strip=False):
        """
        Returns a MIB name based on an OID and special handling flags.

        @param oid: SNMP Object IDentifier
        @type oid: string
        @param exactMatch: find the full OID or don't match
        @type exactMatch: boolean
        @param strip: show what matched, or matched + numeric OID remainder
        @type strip: boolean
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        if isinstance(oid, tuple):
            oid = '.'.join(map(str, oid))

        oid = oid.strip('.')
        if exactMatch:
            if oid in self.oidMap:
                return self.oidMap[oid]
            else:
                return oid

        oidlist = oid.split('.')
        for i in range(len(oidlist), 0, -1):
            name = self.oidMap.get('.'.join(oidlist[:i]), None)
            if name is None:
                continue

            oid_trail = oidlist[i:]
            if len(oid_trail) > 0 and not strip:
                return "%s.%s" % (name, '.'.join(oid_trail))
            else:
                return name

        return oid

    def _pre_parse(self, session, transport, transport_data, transport_data_length):
        """Called before the net-snmp library parses the PDU. In the case
        where a v3 trap comes in with unkwnown credentials, net-snmp silently
        discards the packet. This method gives zentrap a way to log that these
        packets were received to help with troubleshooting."""
        if self.log.isEnabledFor(logging.DEBUG):
            ipv6_socket_address = c.cast(transport_data, c.POINTER(sockaddr_in6)).contents
            if ipv6_socket_address.family == socket.AF_INET6:
                self.log.debug("pre_parse: IPv6 %s" % (socket.inet_ntop(socket.AF_INET6, ipv6_socket_address.addr)))
            elif ipv6_socket_address.family == socket.AF_INET:
                ipv4_socket_address = c.cast(transport_data, c.POINTER(sockaddr_in)).contents
                self.log.debug("pre_parse: IPv4 %s" % socket.inet_ntop(socket.AF_INET, ipv4_socket_address.addr))
            else:
                self.log.debug("pre_parse: unexpected address family: %s" % ipv6_socket_address.family)
        return 1

    def receiveTrap(self, pdu):
        """
        Accept a packet from the network and spin off a Twisted
        deferred to handle the packet.

        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        """
        if pdu.version not in (SNMPv1, SNMPv2, SNMPv3):
            self.log.error("Unable to handle trap version %d", pdu.version)
            return
        if pdu.transport_data is None:
            self.log.error("PDU does not contain transport data")
            return

        ipv6_socket_address = c.cast(pdu.transport_data, c.POINTER(sockaddr_in6)).contents
        if ipv6_socket_address.family == socket.AF_INET6:
            if pdu.transport_data_length < c.sizeof(sockaddr_in6):
                self.log.error("PDU transport data is too small for sockaddr_in6 struct.")
                return
            ip_address = self.getPacketIp(ipv6_socket_address.addr)
        elif ipv6_socket_address.family == socket.AF_INET:
            if pdu.transport_data_length < c.sizeof(sockaddr_in):
                self.log.error("PDU transport data is too small for sockaddr_in struct.")
                return
            ipv4_socket_address = c.cast(pdu.transport_data, c.POINTER(sockaddr_in)).contents
            ip_address = '.'.join(str(i) for i in ipv4_socket_address.addr)
        else:
            self.log.error("Got a packet with unrecognized network family: %s", ipv6_socket_address.family)
            return

        port = socket.ntohs(ipv6_socket_address.port)
        self.log.debug( "Received packet from %s at port %s" % (ip_address, port) )
        self.processPacket(ip_address, port, pdu, time.time())
        # update our total events stats
        totalTime, totalEvents, maxTime = self.stats.report()
        stat = self._statService.getStatistic("events")
        stat.value = totalEvents

    def getPacketIp(self, addr):
        """
        For IPv4, convert a pointer to 4 bytes to a dotted-ip-address
        For IPv6, convert a pointer to 16 bytes to a canonical IPv6 address.
        """

        def _gen_byte_pairs():
            for left, right in zip(addr[::2], addr[1::2]):
                yield "%.2x%.2x" % (left, right)

        v4_mapped_prefix = [0x00] * 10 + [0xff] * 2
        if addr[:len(v4_mapped_prefix)] == v4_mapped_prefix:
            ip_address = '.'.join(str(i) for i in addr[-4:])
        else:
            try:
                basic_v6_address = ':'.join(_gen_byte_pairs())
                ip_address = str(IPAddress(basic_v6_address, 6))
            except ValueError:
                self.log.warn("The IPv6 address is incorrect: %s", addr[:])
                ip_address = "::"
        return ip_address

    def processPacket(self, ip_address, port, pdu, ts):
        """
        Wrapper around asyncHandleTrap to process the provided packet.

        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        @param ts: time stamp
        @type ts: datetime
        """
        # At the end of this callback, pdu will be deleted, so copy it
        # for asynchronous processing
        dup = netsnmp.lib.snmp_clone_pdu(c.byref(pdu))
        if not dup:
            self.log.error("Could not clone PDU for asynchronous processing")
            return

        def cleanup(result):
            """
            Twisted callback to delete a previous memory allocation

            @param result: Net-SNMP object
            @type result: netsnmp_pdu object
            @return: the result parameter
            @rtype: binary
            """
            netsnmp.lib.snmp_free_pdu(dup)
            return result

        d = defer.maybeDeferred(self.asyncHandleTrap, (ip_address, port), dup.contents, ts)
        d.addBoth(cleanup)

    def _value_from_dateandtime(self, value):
        """
        Tries converting a DateAndTime value to a printable string.

        A date-time specification.
        field  octets  contents                  range
        -----  ------  --------                  -----
        1      1-2     year*                     0..65536
        2        3     month                     1..12
        3        4     day                       1..31
        4        5     hour                      0..23
        5        6     minutes                   0..59
        6        7     seconds                   0..60
                      (use 60 for leap-second)
        7        8     deci-seconds              0..9
        8        9     direction from UTC        '+' / '-'
        9       10     hours from UTC*           0..13
        10      11     minutes from UTC          0..59
        """
        # Some traps send invalid UTC times (direction/hours/minutes all zeros)
        if value[8:] == '\x00\x00\x00':
            value = value[:8]
        vallen = len(value)
        if vallen == 8 or (vallen == 11 and value[8] in ('+','-')):
            (year, mon, day, hour, mins, secs, dsecs) = unpack(">HBBBBBB", value[:8])
            # Ensure valid date representation
            if mon < 1 or mon > 12:
                return None
            if day < 1 or day > 31:
                return None
            if hour < 0 or hour > 23:
                return None
            if mins > 60:
                return None
            if secs > 60:
                return None
            if dsecs > 9:
                return None
            if vallen == 11:
                utc_dir = value[8]
                (utc_hours, utc_mins) = unpack(">BB", value[9:])
            else:
                tz_mins = time.timezone / 60
                if tz_mins < 0:
                    utc_dir = '-'
                    tz_mins = -tz_mins
                else:
                    utc_dir = '+'
                utc_hours = tz_mins / 60
                utc_mins = tz_mins % 60
            return "%04d-%02d-%02dT%02d:%02d:%02d.%d00%s%02d:%02d" % (year,
                mon, day, hour, mins, secs, dsecs, utc_dir, utc_hours, utc_mins)

    def _convert_value(self, value):
        if not isinstance(value, basestring):
            return value
        try:
            value.decode('utf8')
            return value
        except UnicodeDecodeError:
            # Try converting to a date
            decoded = self._value_from_dateandtime(value)
            if not decoded:
                decoded = 'BASE64:' + base64.b64encode(value)
            return decoded

    def snmpInform(self, addr, pdu):
        """
        A SNMP trap can request that the trap recipient return back a response.
        This is where we do that.
        """
        reply = netsnmp.lib.snmp_clone_pdu(c.byref(pdu))
        if not reply:
            self.log.error("Could not clone PDU for INFORM response")
            raise RuntimeError("Cannot respond to INFORM PDU")
        reply.contents.command = netsnmp.SNMP_MSG_RESPONSE
        reply.contents.errstat = 0
        reply.contents.errindex = 0

        # FIXME: might need to add udp6 for IPv6 addresses
        sess = netsnmp.Session(peername='%s:%d' % tuple(addr),
                               version=pdu.version)
        sess.open()
        if not netsnmp.lib.snmp_send(sess.sess, reply):
            netsnmp.lib.snmp_sess_perror("Unable to send inform PDU",
                                         self.session.sess)
            netsnmp.lib.snmp_free_pdu(reply)
        sess.close()

    def _add_varbind_detail(self, result, oid, value):
        # Add a detail for the variable binding.
        detail_name = self.oid2name(oid, exactMatch=False, strip=False)
        result[detail_name].append(str(value))

        # Add a detail for the index-stripped variable binding.
        detail_name_stripped = self.oid2name(oid, exactMatch=False, strip=True)
        if detail_name_stripped != detail_name:
            result[detail_name_stripped].append(str(value))

    def decodeSnmpv1(self, addr, pdu):
        result = {"snmpVersion": "1"}

        variables = self.getResult(pdu)

        # Sometimes the agent_addr is useless.
        # Use addr[0] unchanged in this case.
        # Note that SNMPv1 packets *cannot* come in via IPv6
        new_addr = '.'.join(map(str, [pdu.agent_addr[i] for i in range(4)]))
        result["device"] = addr[0] if new_addr == "0.0.0.0" or new_addr.startswith('127') else new_addr

        enterprise = self.getEnterpriseString(pdu)
        generic = pdu.trap_type
        specific = pdu.specific_type

        result["snmpV1Enterprise"] = enterprise
        result["snmpV1GenericTrapType"] = generic
        result["snmpV1SpecificTrap"] = specific

        # Try an exact match with a .0. inserted between enterprise and
        # specific OID. It seems that MIBs frequently expect this .0.
        # to exist, but the device's don't send it in the trap.
        result["oid"] = "%s.0.%d" % (enterprise, specific)
        name = self.oid2name(result["oid"], exactMatch=True, strip=False)

        # If we didn't get a match with the .0. inserted we will try
        # resolving with the .0. inserted and allow partial matches.
        if name == result["oid"]:
            result["oid"] = "%s.%d" % (enterprise, specific)
            name = self.oid2name(result["oid"], exactMatch=False, strip=False)

        # Look for the standard trap types and decode them without
        # relying on any MIBs being loaded.
        eventType = {
            0: 'snmp_coldStart',
            1: 'snmp_warmStart',
            2: 'snmp_linkDown',
            3: 'snmp_linkUp',
            4: 'snmp_authenticationFailure',
            5: 'snmp_egpNeighorLoss',
            6: name,
        }.get(generic, name)

        # Decode all variable bindings. Allow partial matches and strip
        # off any index values.
        vb_result = defaultdict(list)
        for vb_oid, vb_value in variables:
            vb_value = self._convert_value(vb_value)
            vb_oid = '.'.join(map(str, vb_oid))
            self._add_varbind_detail(vb_result, vb_oid, vb_value)

        result.update({name:','.join(vals) for name, vals in vb_result.iteritems()})
        return eventType, result

    def decodeSnmpv2(self, addr, pdu):
        eventType = 'unknown'
        result = {"snmpVersion": "2", "oid": "", "device": addr[0]}
        variables = self.getResult(pdu)

        vb_result = defaultdict(list)
        for vb_oid, vb_value in variables:
            vb_value = self._convert_value(vb_value)
            vb_oid = '.'.join(map(str, vb_oid))
            # SNMPv2-MIB/snmpTrapOID
            if vb_oid == '1.3.6.1.6.3.1.1.4.1.0':
                result["oid"] = '.'.join(map(str, vb_value))
                eventType = self.oid2name(
                        vb_value, exactMatch=False, strip=False)
            else:
                self._add_varbind_detail(vb_result, vb_oid, vb_value)
        result.update({name:','.join(vals) for name, vals in vb_result.iteritems()})

        if eventType in ["linkUp", "linkDown"]:
            eventType = "snmp_" + eventType
        return eventType, result

    def asyncHandleTrap(self, addr, pdu, startProcessTime):
        """
        Twisted callback to process a trap

        @param addr: packet-sending host's IP address, port info
        @type addr: ( host-ip, port)
        @param pdu: Net-SNMP object
        @type pdu: netsnmp_pdu object
        @param startProcessTime: time stamp
        @type startProcessTime: datetime
        @return: Twisted deferred object
        @rtype: Twisted deferred object
        """
        self.capturePacket(addr[0], addr, pdu)

        # Some misbehaving agents will send SNMPv1 traps contained within
        # an SNMPv2c PDU. So we can't trust tpdu.version to determine what
        # version trap exists within the PDU. We need to assume that a
        # PDU contains an SNMPv1 trap if the enterprise_length is greater
        # than zero in addition to the PDU version being 0.
        if pdu.version == SNMPv1 or pdu.enterprise_length > 0:
            self.log.debug("SNMPv1 trap, Addr: %s PDU Agent Addr: %s", str(addr), str(pdu.agent_addr))
            eventType, result = self.decodeSnmpv1(addr, pdu)
        elif pdu.version in (SNMPv2, SNMPv3):
            self.log.debug("SNMPv2 or v3 trap, Addr: %s", str(addr))
            eventType, result = self.decodeSnmpv2(addr, pdu)
        else:
            self.log.error("Unable to handle trap version %d", pdu.version)
            return
        self.log.debug("asyncHandleTrap: eventType=%s oid=%s snmpVersion=%s", eventType, result['oid'], result['snmpVersion'])

        community = self.getCommunity(pdu)
        self.sendTrapEvent(result, community, eventType,
                           startProcessTime)

        if self.isReplaying():
            self.replayed += 1
            # Don't attempt to respond back if we're replaying packets
            return

        if pdu.command == netsnmp.SNMP_MSG_INFORM:
            self.snmpInform(addr, pdu)

    def sendTrapEvent(self, result, community, eventType, startProcessTime):
        summary = 'snmp trap %s' % eventType
        self.log.debug(summary)
        result.setdefault('component', '')
        result.setdefault('eventClassKey', eventType)
        result.setdefault('eventGroup', 'trap')
        result.setdefault('severity', SEVERITY_WARNING)
        result.setdefault('summary', summary)
        result.setdefault('community', community)
        result.setdefault('firstTime', startProcessTime)
        result.setdefault('lastTime', startProcessTime)
        result.setdefault('monitor', self.options.monitor)
        self._eventService.sendEvent(result)
        self.stats.add(time.time() - startProcessTime)

    def displayStatistics(self):
        totalTime, totalEvents, maxTime = self.stats.report()
        display = "%d events processed in %.2f seconds" % (
                      totalEvents,
                      totalTime)
        if totalEvents > 0:
            display += """
%.5f average seconds per event
Maximum processing time for one event was %.5f""" % (
                       (totalTime / totalEvents), maxTime)
        return display

    def cleanup(self):
        if self.session:
            self.session.close()
        status = self.displayStatistics()
        self.log.info(status)


class MibConfigTask(ObservableMixin):
    """
    Receive a configuration object containing MIBs and update the
    mapping of OIDs to names.
    """
    zope.interface.implements(IScheduledTask)

    def __init__(self, taskName, configId,
                 scheduleIntervalSeconds=3600, taskConfig=None):
        super(MibConfigTask, self).__init__()

        # Needed for ZCA interface contract
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds
        self._preferences = taskConfig
        self._daemon = zope.component.getUtility(ICollector)

        self._daemon.oidMap = self._preferences.oidMap

    def doTask(self):
        return defer.succeed("Already updated OID -> name mappings...")

    def cleanup(self):
        pass


class BaseFilterDefinition(object):
    def __init__(self, lineNumber=None, action=None):
        self.lineNumber =  lineNumber
        self.action = action

class GenericTrapFilter(BaseFilterDefinition):
    def __init__(self, lineNumber=None, action=None, genericTrap=None):
        BaseFilterDefinition.__init__(self, lineNumber, action)
        self.genericTrap = genericTrap

    def __eq__(self, other):
        """
        >>> base1 = GenericTrapFilter(0, "include", "1")
        >>> base2 = GenericTrapFilter(0, "include", "1")
        >>> print base1 == base2
        True
        >>> base1 = GenericTrapFilter(0, "include", "1")
        >>> base2 = GenericTrapFilter(0, "include", "2")
        >>> print base1 == base2
        False

        If the traps are the same but actions are different, they are still equal
        >>> base1 = GenericTrapFilter(0, "include", "1")
        >>> base2 = GenericTrapFilter(0, "exclude", "1")
        >>> print base1 == base2
        True
        >>> base1 = GenericTrapFilter(0, "include", "1")
        >>> base2 = BaseFilterDefinition(0, "include")
        >>> print base1 == base2
        False
        """
        if isinstance(other, GenericTrapFilter):
            return self.genericTrap == other.genericTrap
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        """
        >>> base1 = GenericTrapFilter(0, "include", "1")
        >>> base2 = GenericTrapFilter(0, "include", "1")
        >>> print  base1.__hash__() == base2.__hash__()
        True
        >>> base1 = GenericTrapFilter(0, "include", "1")
        >>> base2 = GenericTrapFilter(0, "include", "2")
        >>> print  base1.__hash__() == base2.__hash__()
        False

        If the traps are the same but actions are different, they are still equal
        >>> base1 = GenericTrapFilter(0, "include", "1")
        >>> base2 = GenericTrapFilter(0, "exclude", "1")
        >>> print  base1.__hash__() == base2.__hash__()
        True
        """
        return hash(self.genericTrap)

class OIDBasedFilter(BaseFilterDefinition):
    def __init__(self, lineNumber=None, action=None, oid=None):
        BaseFilterDefinition.__init__(self, lineNumber, action)
        self.oid = oid

    def levels(self):
        return self.oid.count(".") if self.oid else 0

    def __eq__(self, other):
        """
        >>> base1 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> base2 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> print  base1 == base2
        True
        >>> base1 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> base2 = OIDBasedFilter(0, "include", "5.4.3.2.1")
        >>> print  base1 == base2
        False

        If the oids are the same but actions are different, they are still equal
        >>> base1 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> base2 = OIDBasedFilter(0, "exclude", "1.2.3.4.5")
        >>> print  base1 == base2
        True
        >>> base1 = OIDBasedFilter(0, "include", "1")
        >>> base2 = BaseFilterDefinition(0, "include")
        >>> print  base1 == base2
        False
        """
        if isinstance(other, OIDBasedFilter):
            return self.oid == other.oid
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        """
        >>> base1 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> base2 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> print  base1.__hash__() == base2.__hash__()
        True
        >>> base1 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> base2 = OIDBasedFilter(0, "include", "5.4.3.2.1")
        >>> print  base1.__hash__() == base2.__hash__()
        False

        If the oids are the same but actions are different, they are still equal
        >>> base1 = OIDBasedFilter(0, "include", "1.2.3.4.5")
        >>> base2 = OIDBasedFilter(0, "exclude", "1.2.3.4.5")
        >>> print  base1.__hash__() == base2.__hash__()
        True
        """
        return hash(self.oid)

class V1Filter(OIDBasedFilter):
    def __init__(self, lineNumber=None, action=None, oid=None):
        OIDBasedFilter.__init__(self, lineNumber, action, oid)
        self.specificTrap = None

class V2Filter(OIDBasedFilter):
    def __init__(self, lineNumber=None, action=None, oid=None):
        OIDBasedFilter.__init__(self, lineNumber, action, oid)

class TrapFilter(object):
    implements(ICollectorEventTransformer)
    """
    Interface used to perform filtering of events at the collector. This could be
    used to drop events, transform event content, etc.

    These transformers are run sequentially before a fingerprint is generated for
    the event, so they can set fields which are used by an ICollectorEventFingerprintGenerator.

    The priority of the event transformer (the transformers are executed in
    ascending order using the weight of each filter).
    """
    weight = 1
    def __init__(self):
        self._daemon = None
        self._eventService = None
        self._oids = set()

        # Map of SNMP V1 Generic Trap filters where key is the generic trap number and value is a GenericTrapFilter
        self._v1Traps = dict()

        # Map of SNMP V1 enterprise-specific traps where key is the count of levels in an OID, and
        # value is a map of unique V1Filter objects for that number of OID levels. The map of V1Filter objects is keyed
        # by OID
        self._v1Filters = dict()
        self._v2Filters = dict()
        self._initialized = False

    def _parseFilterDefinition(self, line, lineNumber):
        """
           Parse an SNMP filter definition of the format
           include|exclude v1|v2 <version-specific options

        @param line: The filter definition to parse
        @type line: string
        @param lineNumber: The line number of the filter defintion within the file
        @type line: int
        @return: Returns None on success, or an error message on failure
        @rtype: string

        >>> filter = TrapFilter()
        >>> print  _parseFilterDefinition("a b", 0)
        Incomplete definition at line 0
        """
        tokens = line.split()
        if len(tokens) < 3:
            return "Incomplete definition at line %d" % lineNumber

        action = tokens[0].lower()
        snmpVersion = tokens[1].lower()
        if action != "include" and action != "exclude":
            return "Invalid action '%s' at line %d; the only valid actions are 'include' or 'exclude'" % (action, lineNumber)
        elif snmpVersion != "v1" and snmpVersion != "v2":
            return "Invalid SNMP version '%s' at line %d" % (snmpVersion, lineNumber)

        if snmpVersion == "v1":
            return self._parseV1Filter(lineNumber, action, tokens[2:])

        return self._parseV2Filter(lineNumber, action, tokens[2:])

    def _parseV1Filter(self, lineNumber, action, remainingTokens):
        """
           Parse an SNMP V1 filter definition

        @param lineNumber: The line number of the filter defintion within the file
        @type line: int
        @param action: The action for this line (include or exclude)
        @type line: string
        @param remainingTokens: The remaining (unparsed) tokens from the filter definition
        @type line: string array
        @return: Returns None on success, or an error message on failure
        @rtype: string

        >>> filter = TrapFilter()
        >>> print  _parseV1Filter(0, "include", ['a', 'b', 'c'])
        Too many fields found at line 0; at most 4 fields allowed for V1 filters
        """
        if len(remainingTokens) > 2:
            return "Too many fields found at line %d; at most 4 fields allowed for V1 filters" % lineNumber

        oidOrGenericTrap = remainingTokens[0].strip(".")
        if not oidOrGenericTrap:
            return "Empty OID at line %d" % lineNumber

        if len(oidOrGenericTrap) == 1:
            if not oidOrGenericTrap.isDigit() or not oidOrGenericTrap in "012345":
                return "Invalid generic trap %s at line %d; must be one of 0-5" % (oidOrGenericTrap, lineNumber)

            genericTrap = GenericTrapFilter(lineNumber, action, oidOrGenericTrap)
            if genericTrap in self._v1Traps:
                return "Generic trap %s at line %d conflicts with previous definition at line %d" & (oidOrGenericTrap, lineNumber, self._v1Traps.get(genericTrap).lineNumber)

            self._v1Traps.add(genericTrap)
            return True

        v1FilterDef = V1Filter(lineNumber, action, oidOrGenericTrap)
        if len(remainingTokens) == 2:
            v1FilterDef.specificTrap = remainingTokens[1]

        if v1FilterDef in self._v1Filters:
            return "V1 trap %s at line %d conflicts with previous definition at line %d" % (oidOrGenericTrap, lineNumber, self._v1Filters.get(v1FilterDef).lineNumber)

        self._v1Filters.add(v1FilterDef)
        return None

    def _parseV2Filter(self, lineNumber, action, remainingTokens):
        """
           Parse an SNMP V2 filter definition

        @param lineNumber: The line number of the filter defintion within the file
        @type line: int
        @param action: The action for this line (include or exclude)
        @type line: string
        @param remainingTokens: The remaining (unparsed) tokens from the filter definition
        @type line: string array
        @return: Returns None on success, or an error message on failure
        @rtype: string

        >>> filter = TrapFilter()
        >>> print  _parseV2Filter(0, "include", ['a', 'b'])
        Too many fields found at line 0; at most 3 fields allowed for V2 filters
        """
        if len(remainingTokens) > 1:
            return "Too many fields found at line %d; at most 3 fields allowed for V2 filters" % lineNumber

        oid = remainingTokens[0].strip(".")
        if not oid:
            return "Empty OID at line %d" % lineNumber

        v2FilterDef = V2Filter(lineNumber, action, oid)

        mapByLevel = self._v2Filters.get(v2FilterDef.levels(), None)
        if mapByLevel == None:
            mapByLevel[oid] = {oid: v2FilterDef}
            self._v2Filters.update({v2FilterDef.levels(), mapByLevel})
        elif not mapByLevel[oid]:
            mapByLevel[oid] = v2FilterDef
        else:
            return "V2 trap %s at line %d conflicts with previous definition at line %d" % (oid, lineNumber, mapByLevel[oid].lineNumber)
        return None

    def _read_filters(self):
        oids = set()
        fileName = self._daemon.options.trapFilterFile
        if fileName:
            path = zenPath('etc', fileName)
            if os.path.exists(path):
                with open(path) as oidFile:
                    lineNumber = 0
                    for line in oidFile:
                        lineNumber += 1
                        if line.startswith('#'):
                            continue

                        # remove leading and trailing whitespace, dots
                        line = line.strip()
                        if not line:
                            continue;

                        oids.add(line)
                        #if not self._parseFilterLine(line, lineNumber):
                        #    log.error("Failed tp parse filter file %s at line %d. Exiting.", format(path), lineNumber)
                        #    sys.exit(1)

                log.info("Found %d filters in %s", len(oids), format(path))
            else:
                log.warn("Config file {0} was not found; no zentrap filters added.".format(path))
        return oids

    def initialize(self):
        self._daemon = zope.component.getUtility(ICollector)
        self._eventService = zope.component.queryUtility(IEventService)
        self._oids = self._read_filters()
        self._initialized = True

    def transform(self, event):
        """
        Performs any transforms of the specified event at the collector.

        @param event: The event to transform.
        @type event: dict
        @return: Returns TRANSFORM_CONTINUE if this event should be forwarded on
                 to the next transformer in the sequence, TRANSFORM_STOP if no
                 further transformers should be performed on this event, and
                 TRANSFORM_DROP if the event should be dropped.
        @rtype: int
        """
        result = TRANSFORM_CONTINUE
        trapOid = event.get('oid', None)
        if trapOid and self._initialized and self._oids:
            log.debug("Filtering V%s trap %s", event.get('snmpVersion', "undefined"), trapOid)
            if self._dropOid(trapOid):
                log.debug("Dropping trap %s", trapOid)
                result = TRANSFORM_DROP
        else:
            log.debug("Skipping filter for oid=%s, initialized=%s len(oids)=%d",
                trapOid, self._initialized, len(self._oids))
        return result

    def _dropOid(self, oid):
        return oid not in self._oids

class TrapDaemon(CollectorDaemon):

    _frameworkFactoryName = "nosip"

    def __init__(self, *args, **kwargs):
        self._trapFilter = TrapFilter()
        zope.component.provideUtility(self._trapFilter, ICollectorEventTransformer)
        super(TrapDaemon, self).__init__(*args, **kwargs)
        self._trapFilter.initialize()

    def runPostConfigTasks(self, result=None):
        # 1) super sets self._prefs.task with the call to postStartupTasks
        # 2) call remote createAllUsers
        # 3) service in turn walks DeviceClass tree and returns users
        CollectorDaemon.runPostConfigTasks(self, result)
        if not isinstance(result, Failure) and self._prefs.task is not None:
            service = self.getRemoteConfigServiceProxy()
            log.debug('TrapDaemon.runPostConfigTasks callRemote createAllUsers')
            d = service.callRemote("createAllUsers")
            d.addCallback(self._createUsers)

    def remote_createUser(self, user):
        self._createUsers([user])

    def _createUsers(self, users):
        fmt = 'TrapDaemon._createUsers {0} users'
        count = len(users)
        log.debug(fmt.format(count))
        if self._prefs.task.session is None:
            log.debug("No session created, so unable to create users")
        else:
            self._prefs.task.session.create_users(users)


if __name__=='__main__':
    myPreferences = SnmpTrapPreferences()
    myTaskFactory = SimpleTaskFactory(MibConfigTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = TrapDaemon(myPreferences, myTaskSplitter)
    daemon.run()
