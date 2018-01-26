##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, 2011-2012, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""zentrap

Creates events from SNMP Traps.
Currently a wrapper around the Net-SNMP C library.
"""

import base64
import ctypes as c  # Magical interfacing with C code
import errno
import logging
import socket
import sys
import time

from collections import defaultdict
from ipaddr import IPAddress
from struct import unpack

from pynetsnmp import netsnmp, twistedsnmp
from twisted.internet import defer
from twisted.python.failure import Failure
from zope.component import queryUtility, getUtility, provideUtility
from zope.interface import implementer

from zenoss.protocols.protobufs.zep_pb2 import SEVERITY_WARNING

import Globals

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import (
    ICollector, ICollectorPreferences, IEventService,
    IScheduledTask, IStatisticsService
)
from Products.ZenCollector.services.config import DeviceProxy
from Products.ZenCollector.tasks import (
    SimpleTaskFactory, SimpleTaskSplitter, BaseTask, TaskStates
)
from Products.ZenEvents.EventServer import Stats
from Products.ZenEvents.TrapFilter import TrapFilter, TrapFilterError
from Products.ZenEvents.ZenEventClasses import Clear, Critical
from Products.ZenHub.interfaces import ICollectorEventTransformer
from Products.ZenHub.services.SnmpTrapConfig import User
from Products.ZenUtils.captureReplay import CaptureReplay
from Products.ZenUtils.observable import ObservableMixin
from Products.ZenUtils.Utils import unused

unused(Globals, DeviceProxy, User)

log = logging.getLogger("zen.zentrap")

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


_pre_parse_factory = c.CFUNCTYPE(
    c.c_int,
    c.POINTER(netsnmp.netsnmp_session),
    c.POINTER(netsnmp.netsnmp_transport),
    c.c_void_p,
    c.c_int
)

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


@implementer(ICollectorPreferences)
class SnmpTrapPreferences(CaptureReplay):

    def __init__(self):
        """
        Initializes a SnmpTrapPreferences instance and provides
        default values for needed attributes.
        """
        self.collectorName = 'zentrap'
        self.configCycleInterval = 20  # minutes
        self.cycleInterval = 5 * 60  # seconds

        # The configurationService attribute is the fully qualified class-name
        # of our configuration service that runs within ZenHub
        self.configurationService = 'Products.ZenHub.services.SnmpTrapConfig'

        # Will be filled in based on buildOptions
        self.options = None

        self.configCycleInterval = 20 * 60
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
        parser.add_option(
            '--trapport', '-t',
            dest='trapport', type='int', default=TRAP_PORT,
            help="Listen for SNMP traps on this port rather than the default"
        )
        parser.add_option(
            '--useFileDescriptor',
            dest='useFileDescriptor', type='int', default=None,
            help="Read from an existing connection "
            "rather than opening a new port."
        )
        parser.add_option(
            '--trapFilterFile',
            dest='trapFilterFile', type='string', default=None,
            help="File that contains trap oids to keep, "
            "should be in $ZENHOME/etc."
        )

        self.buildCaptureReplayOptions(parser)

    def postStartup(self):
        # Ensure that we always have an oidMap
        daemon = getUtility(ICollector)
        daemon.oidMap = {}
        # add our collector's custom statistics
        statService = queryUtility(IStatisticsService)
        statService.addStatistic("events", "COUNTER")


def ipv6_is_enabled():
    """test if ipv6 is enabled
    """
    # hack for ZEN-12088 - TODO: remove next line
    return False
    try:
        socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, 0)
    except socket.error as e:
        if e.errno == errno.EAFNOSUPPORT:
            return False
        raise
    return True


@implementer(IScheduledTask)
class TrapTask(BaseTask, CaptureReplay):
    """
    Listen for SNMP traps and turn them into events
    Connects to the TrapService service in zenhub.
    """

    def __init__(
            self, taskName, configId, scheduleIntervalSeconds=3600,
            taskConfig=None):
        BaseTask.__init__(
            self, taskName, configId, scheduleIntervalSeconds, taskConfig
        )
        self.log = log

        # Needed for interface
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds
        self._daemon = getUtility(ICollector)
        self._eventService = queryUtility(IEventService)
        self._preferences = self._daemon
        self._statService = queryUtility(IStatisticsService)
        # For compatibility with captureReplay
        self.options = self._daemon.options
        self.oidMap = self._daemon.oidMap
        self.stats = Stats()

        # Command-line argument sanity checking
        self.processCaptureReplayOptions()
        self.session = None
        self._replayStarted = False
        if not self.options.replayFilePrefix:
            trapPort = self._preferences.options.trapport
            if not self.options.useFileDescriptor and trapPort < 1024:
                listen_ip = "ipv6" if ipv6_is_enabled() else "0.0.0.0"
                # Makes call to zensocket here
                # does an exec* so it never returns
                self._daemon.openPrivilegedPort(
                    '--listen',
                    '--proto=udp',
                    '--port=%s:%d' % (listen_ip, trapPort)
                )
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
            self.session.awaitTraps(
                listening_address, fileno, self._pre_parse_callback, debug
            )
            self.session.callback = self.receiveTrap
            twistedsnmp.updateReactor()

    def doTask(self):
        """
        This is a wait-around task since we really are called
        asynchronously.
        """
        if self.options.replayFilePrefix and not self._replayStarted:
            log.debug("Replay starting...")
            self._replayStarted = True
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
        if hasattr(pdu, "fake"):  # Replaying a packet
            return pdu.enterprise
        return '.'.join(
            str(pdu.enterprise[i]) for i in range(pdu.enterprise_length)
        )

    def getResult(self, pdu):
        """
        Get the values from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: variables from the PDU or Fake packet
        @rtype: dictionary
        """
        if hasattr(pdu, "fake"):  # Replaying a packet
            return pdu.variables
        return netsnmp.getResult(pdu)

    def getCommunity(self, pdu):
        """
        Get the community string from the PDU or replayed packet

        @param pdu: raw packet
        @type pdu: binary
        @return: SNMP community
        @rtype: string
        """
        if hasattr(pdu, "fake"):  # Replaying a packet
            return pdu.community
        elif pdu.community_len:
            return c.string_at(pdu.community, pdu.community_len)
        return ''

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
            packet.agent_addr = [pdu.agent_addr[i] for i in range(4)]
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
            return self.oidMap.get(oid, oid)

        oidlist = oid.split('.')
        for i in range(len(oidlist), 0, -1):
            name = self.oidMap.get('.'.join(oidlist[:i]), None)
            if name is None:
                continue

            oid_trail = oidlist[i:]
            if len(oid_trail) > 0 and not strip:
                return "%s.%s" % (name, '.'.join(oid_trail))
            return name

        return oid

    def _pre_parse(
            self, session, transport, transport_data, transport_data_length):
        """Called before the net-snmp library parses the PDU. In the case
        where a v3 trap comes in with unkwnown credentials, net-snmp silently
        discards the packet. This method gives zentrap a way to log that these
        packets were received to help with troubleshooting.
        """
        if self.log.isEnabledFor(logging.DEBUG):
            ipv6_socket_address = c.cast(
                transport_data, c.POINTER(sockaddr_in6)
            ).contents
            if ipv6_socket_address.family == socket.AF_INET6:
                self.log.debug(
                    "pre_parse: IPv6 %s",
                    socket.inet_ntop(
                        socket.AF_INET6, ipv6_socket_address.addr
                    )
                )
            elif ipv6_socket_address.family == socket.AF_INET:
                ipv4_socket_address = c.cast(
                    transport_data, c.POINTER(sockaddr_in)
                ).contents
                self.log.debug(
                    "pre_parse: IPv4 %s",
                    socket.inet_ntop(socket.AF_INET, ipv4_socket_address.addr)
                )
            else:
                self.log.debug(
                    "pre_parse: unexpected address family: %s",
                    ipv6_socket_address.family
                )
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

        ipv6_socket_address = c.cast(
            pdu.transport_data, c.POINTER(sockaddr_in6)
        ).contents
        if ipv6_socket_address.family == socket.AF_INET6:
            if pdu.transport_data_length < c.sizeof(sockaddr_in6):
                self.log.error(
                    "PDU transport data is too small for sockaddr_in6 struct."
                )
                return
            ip_address = self.getPacketIp(ipv6_socket_address.addr)
        elif ipv6_socket_address.family == socket.AF_INET:
            if pdu.transport_data_length < c.sizeof(sockaddr_in):
                self.log.error(
                    "PDU transport data is too small for sockaddr_in struct."
                )
                return
            ipv4_socket_address = c.cast(
                pdu.transport_data, c.POINTER(sockaddr_in)
            ).contents
            ip_address = '.'.join(str(i) for i in ipv4_socket_address.addr)
        else:
            self.log.error(
                "Got a packet with unrecognized network family: %s",
                ipv6_socket_address.family
            )
            return

        port = socket.ntohs(ipv6_socket_address.port)
        self.log.debug("Received packet from %s at port %s", ip_address, port)
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

        d = defer.maybeDeferred(
            self.asyncHandleTrap, (ip_address, port), dup.contents, ts
        )
        d.addBoth(cleanup)

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
        sess = netsnmp.Session(
            peername='%s:%d' % tuple(addr), version=pdu.version
        )
        sess.open()
        if not netsnmp.lib.snmp_send(sess.sess, reply):
            netsnmp.lib.snmp_sess_perror(
                "Unable to send inform PDU", self.session.sess
            )
            netsnmp.lib.snmp_free_pdu(reply)
        sess.close()

    def _add_varbind_detail(self, result, oid, value):
        detail_name = self.oid2name(oid, exactMatch=False, strip=False)
        result[detail_name].append(str(value))

        detail_name_stripped = self.oid2name(oid, exactMatch=False, strip=True)
        if detail_name_stripped != detail_name:
            remainder = detail_name[len(detail_name_stripped)+1:]
            result[detail_name_stripped + ".sequence"].append(remainder)

    def decodeSnmpv1(self, addr, pdu):

        result = {"snmpVersion": "1"}
        result["device"] = addr[0]

        variables = self.getResult(pdu)

        self.log.debug("SNMPv1 pdu has agent_addr: %s",
                       str(hasattr(pdu, 'agent_addr')))

        if hasattr(pdu, 'agent_addr'):
            origin = '.'.join(str(i) for i in pdu.agent_addr)
            result["device"] = origin

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
            0: 'coldStart',
            1: 'warmStart',
            2: 'snmp_linkDown',
            3: 'snmp_linkUp',
            4: 'authenticationFailure',
            5: 'egpNeighorLoss',
            6: name,
        }.get(generic, name)

        # Decode all variable bindings. Allow partial matches and strip
        # off any index values.
        vb_result = defaultdict(list)
        for vb_oid, vb_value in variables:
            vb_value = decode_snmp_value(vb_value)
            vb_oid = '.'.join(map(str, vb_oid))
            if vb_value is None:
                log.debug(
                    "[decodeSnmpv1] enterprise %s, varbind-oid %s, "
                    "varbind-value %s", enterprise, vb_oid, vb_value
                )
            self._add_varbind_detail(vb_result, vb_oid, vb_value)

        result.update(
            {name: ','.join(vals) for name, vals in vb_result.iteritems()}
        )

        return eventType, result

    def decodeSnmpv2(self, addr, pdu):
        eventType = 'unknown'
        result = {"snmpVersion": "2", "oid": "", "device": addr[0]}
        variables = self.getResult(pdu)

        vb_result = defaultdict(list)
        for vb_oid, vb_value in variables:
            vb_value = decode_snmp_value(vb_value)
            vb_oid = '.'.join(map(str, vb_oid))
            if vb_value is None:
                log.debug(
                    "[decodeSnmpv2] varbind-oid %s, varbind-value %s",
                    vb_oid, vb_value
                )

            # SNMPv2-MIB/snmpTrapOID
            if vb_oid == '1.3.6.1.6.3.1.1.4.1.0':
                result["oid"] = vb_value
                eventType = self.oid2name(
                    vb_value, exactMatch=False, strip=False
                )
            elif vb_oid.startswith('1.3.6.1.6.3.18.1.3'):
                self.log.debug("found snmpTrapAddress OID: %s = %s",
                               vb_oid, vb_value)
                result['snmpTrapAddress'] = vb_value
                result['device'] = vb_value
            else:
                self._add_varbind_detail(vb_result, vb_oid, vb_value)

        result.update(
            {name: ','.join(vals) for name, vals in vb_result.iteritems()}
        )

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
            self.log.debug("SNMPv1 trap, Addr: %s PDU Agent Addr: %s",
                           str(addr), str(pdu.agent_addr))
            eventType, result = self.decodeSnmpv1(addr, pdu)
        elif pdu.version in (SNMPv2, SNMPv3):
            self.log.debug("SNMPv2 or v3 trap, Addr: %s", str(addr))
            eventType, result = self.decodeSnmpv2(addr, pdu)
        else:
            self.log.error("Unable to handle trap version %d", pdu.version)
            return
        self.log.debug("asyncHandleTrap: eventType=%s oid=%s snmpVersion=%s",
                       eventType, result['oid'], result['snmpVersion'])

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
        display = "%d events processed in %.2f seconds" % (totalEvents,
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


class Decoders:
    """methods to decode OID values
    """

    @staticmethod
    def dateandtime(value):
        """Tries converting a DateAndTime value to a printable string.

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
        try:
            dt, tz = value[:8], value[8:]
            if len(dt) != 8 or len(tz) != 3:
                return None
            (year, mon, day, hour, mins, secs, dsecs) = unpack(">HBBBBBB", dt)
            # Ensure valid date representation
            invalid = (
                (mon < 1 or mon > 12),
                (day < 1 or day > 31),
                (hour > 23),
                (mins > 59),
                (secs > 60),
                (dsecs > 9),
            )
            if any(invalid):
                return None
            (utc_dir, utc_hour, utc_min) = unpack(">cBB", tz)
            # Some traps send invalid UTC times (direction is 0)
            if utc_dir == '\x00':
                tz_min = time.timezone / 60
                if tz_min < 0:
                    utc_dir = '-'
                    tz_min = -tz_min
                else:
                    utc_dir = '+'
                utc_hour = tz_min / 60
                utc_min = tz_min % 60
            if utc_dir not in ('+', '-'):
                return None
            return "%04d-%02d-%02dT%02d:%02d:%02d.%d00%s%02d:%02d" % (
                year, mon, day, hour, mins, secs,
                dsecs, utc_dir, utc_hour, utc_min
            )
        except TypeError:
            pass

    @staticmethod
    def oid(value):
        if isinstance(value, tuple) \
                and len(value) > 2 \
                and value[0] in (0, 1, 2) \
                and all(isinstance(i, int) for i in value):
            return '.'.join(map(str, value))

    @staticmethod
    def number(value):
        return value if isinstance(value, (long, int)) else None

    @staticmethod
    def ipaddress(value):
        for version in (socket.AF_INET, socket.AF_INET6):
            try:
                return socket.inet_ntop(version, value)
            except (ValueError, TypeError):
                pass

    @staticmethod
    def utf8(value):
        try:
            return value.decode('utf8')
        except (UnicodeDecodeError, AttributeError):
            pass

    @staticmethod
    def encode_base64(value):
        return 'BASE64:' + base64.b64encode(value)


# NOTE: The order of decoders in the list determines their priority
_decoders = [
    Decoders.oid,
    Decoders.number,
    Decoders.utf8,
    Decoders.ipaddress,
    Decoders.dateandtime,
    Decoders.encode_base64
]


def decode_snmp_value(value):
    """Given a raw OID value
    Itterate over the list of decoder methods in order
    Returns the first value returned by a decoder method
    """
    if value is None:
        return value
    try:
        for decoder in _decoders:
            out = decoder(value)
            if out is not None:
                return out
    except Exception as err:
        log.exception("Unexpected exception: %s", err)


@implementer(IScheduledTask)
class MibConfigTask(ObservableMixin):
    """
    Receive a configuration object containing MIBs and update the
    mapping of OIDs to names.
    """

    def __init__(self, taskName, configId,
                 scheduleIntervalSeconds=3600, taskConfig=None):
        super(MibConfigTask, self).__init__()

        # Needed for ZCA interface contract
        self.name = taskName
        self.configId = configId
        self.state = TaskStates.STATE_IDLE
        self.interval = scheduleIntervalSeconds
        self._preferences = taskConfig
        self._daemon = getUtility(ICollector)

        self._daemon.oidMap = self._preferences.oidMap

    def doTask(self):
        return defer.succeed("Already updated OID -> name mappings...")

    def cleanup(self):
        pass


class TrapDaemon(CollectorDaemon):

    _frameworkFactoryName = "nosip"

    def __init__(self, *args, **kwargs):
        self._trapFilter = TrapFilter()
        provideUtility(self._trapFilter, ICollectorEventTransformer)
        kwargs["initializationCallback"] = self._initializeTrapFilter
        super(TrapDaemon, self).__init__(*args, **kwargs)

    def _initializeTrapFilter(self):
        try:
            self._trapFilter.initialize()
            initializationSucceededEvent = {
                'component': 'zentrap',
                'device': self.options.monitor,
                'eventClass': "/Status",
                'eventKey': "TrapFilterInit",
                'summary': 'initialized',
                'severity': Clear,
            }
            self.sendEvent(initializationSucceededEvent)

        except TrapFilterError as e:
            initializationFailedEvent = {
                'component': 'zentrap',
                'device': self.options.monitor,
                'eventClass': "/Status",
                'eventKey': "TrapFilterInit",
                'summary': 'initialization failed',
                'message': e.message,
                'severity': Critical,
            }

            log.error("Failed to initialize trap filter: %s", e.message)
            self.sendEvent(initializationFailedEvent)
            self.setExitCode(1)
            self.stop()

    def runPostConfigTasks(self, result=None):
        # 1) super sets self._prefs.task with the call to postStartupTasks
        # 2) call remote createAllUsers
        # 3) service in turn walks DeviceClass tree and returns users
        CollectorDaemon.runPostConfigTasks(self, result)
        if not isinstance(result, Failure) and self._prefs.task is not None:
            service = self.getRemoteConfigServiceProxy()
            log.debug('TrapDaemon.runPostConfigTasks '
                      'callRemote createAllUsers')
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


if __name__ == '__main__':
    myPreferences = SnmpTrapPreferences()
    myTaskFactory = SimpleTaskFactory(MibConfigTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = TrapDaemon(myPreferences, myTaskSplitter)
    daemon.run()
