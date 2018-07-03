import base64
import logging

from struct import pack

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.zentrap import (
    decode_snmp_value, TrapTask, FakePacket, SNMPv1, SNMPv2
)

log = logging.getLogger("test_zentrap")


class DecodersUnitTest(BaseTestCase):

    def test_decode_oid(self):
        value = (1, 2, 3, 4)
        self.assertEqual(
            decode_snmp_value(value),
            "1.2.3.4"
        )

    def test_decode_utf8(self):
        value = 'valid utf8 string \xc3\xa9'.encode('utf8')
        self.assertEqual(
            decode_snmp_value(value),
            u'valid utf8 string \xe9'.decode('utf8')
        )

    def test_decode_datetime(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 50, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value),
            '2017-12-20T11:50:50.800+06:05'
        )

    def test_decode_bad_timezone(self):
        value = pack(">HBBBBBBBBB", 2017, 12, 20, 11, 50, 50, 8, 0, 0, 0)
        dttm = decode_snmp_value(value)
        self.assertEqual(dttm[:23], "2017-12-20T11:50:50.800")
        self.assertRegexpMatches(
            dttm[23:], "^[+-][01][0-9]:[0-5][0-9]$"
        )

    def test_decode_invalid_timezone(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 50, 8, '=', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_incomplete_datetime(self):
        value = pack(">HBBBBBB", 2017, 12, 20, 11, 50, 50, 8)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_month_high(self):
        value = pack(">HBBBBBBsBB", 2017, 13, 20, 11, 50, 50, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_month_low(self):
        value = pack(">HBBBBBBsBB", 2017, 0, 20, 11, 50, 50, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_day_high(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 32, 11, 50, 50, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_day_low(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 0, 11, 50, 50, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_hour(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 24, 50, 50, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_minute(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 60, 50, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_bad_second(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 61, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_leap_second(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 60, 8, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), '2017-12-20T11:50:60.800+06:05'
        )

    def test_decode_bad_decisecond(self):
        value = pack(">HBBBBBBsBB", 2017, 12, 20, 11, 50, 50, 10, '+', 6, 5)
        self.assertEqual(
            decode_snmp_value(value), "BASE64:" + base64.b64encode(value)
        )

    def test_decode_value_ipv4(self):
        value = '\xcc\x0b\xc8\x01'
        self.assertEqual(
            decode_snmp_value(value),
            '204.11.200.1'
        )

    def test_decode_value_ipv6(self):
        value = 'Z\xef\x00+\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08'
        self.assertEqual(
            decode_snmp_value(value),
            '5aef:2b::8'
        )

    def test_decode_long_values(self):
        value = long(555)
        self.assertEqual(
            decode_snmp_value(value),
            int(555)
        )

    def test_decode_int_values(self):
        value = int(555)
        self.assertEqual(
            decode_snmp_value(value),
            int(555)
        )

    def test_encode_invalid_chars(self):
        value = '\xde\xad\xbe\xef\xfe\xed\xfa\xce'
        self.assertEqual(
            decode_snmp_value(value),
            'BASE64:3q2+7/7t+s4='
        )

    def test_decode_unexpected_object_type(self):
        value = object()
        self.assertEqual(
            decode_snmp_value(value),
            None
        )


class MockTrapTask(TrapTask):

    def __init__(self, oidMap):
        self.oidMap = oidMap
        self.log = log


class TestOid2Name(BaseTestCase):

    def test_NoExactMatch(self):
        oidMap = {}
        task = MockTrapTask(oidMap)
        self.assertEqual(task.oid2name(".1.2.3.4"), "1.2.3.4")
        self.assertEqual(task.oid2name(".1.2.3.4", strip=True), "1.2.3.4")

    def test_HasExactMatch(self):
        oidMap = {"1.2.3.4": "Zenoss.Test.exactMatch"}
        task = MockTrapTask(oidMap)
        result = task.oid2name(".1.2.3.4")
        self.assertEqual(result, "Zenoss.Test.exactMatch")
        result = task.oid2name(".1.2.3.4", strip=True)
        self.assertEqual(result, "Zenoss.Test.exactMatch")

    def test_NoInexactMatch(self):
        oidMap = {"1.2.3.4": "Zenoss.Test.exactMatch"}
        task = MockTrapTask(oidMap)
        result = task.oid2name(".1.5.3.4", exactMatch=False)
        self.assertEqual(result, "1.5.3.4")

    def test_HasInexactMatchNotStripped(self):
        oidMap = {
            "1.2": "Zenoss",
            "1.2.3": "Zenoss.Test",
            "1.2.3.2": "Zenoss.Test.inexactMatch"
        }
        task = MockTrapTask(oidMap)
        result = task.oid2name(".1.2.3.2.5", exactMatch=False)
        self.assertEqual(result, "Zenoss.Test.inexactMatch.5")
        result = task.oid2name(".1.2.3.2.5.6", exactMatch=False)
        self.assertEqual(result, "Zenoss.Test.inexactMatch.5.6")

    def test_HasInexactMatchStripped(self):
        oidMap = {
            "1.2": "Zenoss",
            "1.2.3": "Zenoss.Test",
            "1.2.3.2": "Zenoss.Test.inexactMatch"
        }
        task = MockTrapTask(oidMap)
        result = task.oid2name(".1.2.3.2.5", exactMatch=False, strip=True)
        self.assertEqual(result, "Zenoss.Test.inexactMatch")
        result = task.oid2name(".1.2.3.2.5.6", exactMatch=False, strip=True)
        self.assertEqual(result, "Zenoss.Test.inexactMatch")

    def test_AcceptsTuple(self):
        oidMap = {}
        task = MockTrapTask(oidMap)
        self.assertEqual(task.oid2name((1, 2, 3, 4)), "1.2.3.4")


class TestDecodeSnmpV1(BaseTestCase):

    def makeInputs(self, trapType=6, oidMap={}, variables=()):
        pckt = FakePacket()
        pckt.version = SNMPv1
        pckt.host = "localhost"
        pckt.port = 162
        pckt.variables = variables
        pckt.community = ""
        pckt.enterprise_length = 0

        # extra fields for SNMPv1 packets
        pckt.agent_addr = [192, 168, 24, 4]
        pckt.trap_type = trapType
        pckt.specific_type = 5
        pckt.enterprise = "1.2.3.4"
        pckt.enterprise_length = len(pckt.enterprise)
        pckt.community = "community"

        return pckt, MockTrapTask(oidMap)

    def test_NoAgentAddr(self):
        pckt, task = self.makeInputs()
        del pckt.agent_addr
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(result["device"], "localhost")

    def test_FieldsNoMappingUsed(self):
        pckt, task = self.makeInputs()
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)

        self.assertEqual(result["device"], "192.168.24.4")
        self.assertEqual(result["snmpVersion"], "1")
        self.assertEqual(result["snmpV1Enterprise"], "1.2.3.4")
        self.assertEqual(result["snmpV1GenericTrapType"], 6)
        self.assertEqual(result["snmpV1SpecificTrap"], 5)
        self.assertEqual(eventType, "1.2.3.4.5")
        self.assertEqual(result["oid"], "1.2.3.4.5")

    def test_EnterpriseOIDWithExtraZero(self):
        pckt, task = self.makeInputs(oidMap={"1.2.3.4.0.5": "testing"})
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "testing")
        self.assertEqual(result["oid"], "1.2.3.4.0.5")

    def test_TrapType0(self):
        pckt, task = self.makeInputs(trapType=0)
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "coldStart")
        self.assertEqual(result["snmpV1GenericTrapType"], 0)

    def test_TrapType1(self):
        pckt, task = self.makeInputs(trapType=1)
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "warmStart")
        self.assertEqual(result["snmpV1GenericTrapType"], 1)

    def test_TrapType2(self):
        pckt, task = self.makeInputs(trapType=2)
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "snmp_linkDown")
        self.assertEqual(result["snmpV1GenericTrapType"], 2)

    def test_TrapType3(self):
        pckt, task = self.makeInputs(trapType=3)
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "snmp_linkUp")
        self.assertEqual(result["snmpV1GenericTrapType"], 3)

    def test_TrapType4(self):
        pckt, task = self.makeInputs(trapType=4)
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "authenticationFailure")
        self.assertEqual(result["snmpV1GenericTrapType"], 4)

    def test_TrapType5(self):
        pckt, task = self.makeInputs(trapType=5)
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "egpNeighorLoss")
        self.assertEqual(result["snmpV1GenericTrapType"], 5)

    def test_TrapType6(self):
        pckt, task = self.makeInputs(trapType=6)
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(eventType, "1.2.3.4.5")
        self.assertEqual(result["snmpV1GenericTrapType"], 6)

    def test_VarBindOneValue(self):
        pckt, task = self.makeInputs(variables=(
            ((1, 2, 6, 7), "foo"),
        ))
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        self.assertEqual(result["1.2.6.7"], "foo")

    def test_VarBindMultiValue(self):
        pckt, task = self.makeInputs(variables=(
            ((1, 2, 6, 7), "foo"),
            ((1, 2, 6, 7), "bar"),
            ((1, 2, 6, 7), "baz"),
        ))
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
        self.assertEqual(totalVarKeys, 1)
        self.assertEqual(result["1.2.6.7"], "foo,bar,baz")

    def test_UnknownMultiVarBind(self):
        pckt, task = self.makeInputs(variables=(
            ((1, 2, 6, 0), "foo"),
            ((1, 2, 6, 1), "bar"),
        ))
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("1.2.6.0", result)
        self.assertIn("1.2.6.1", result)
        self.assertEqual(result["1.2.6.0"], "foo")
        self.assertEqual(result["1.2.6.1"], "bar")

    def test_NamedVarBindOneValue(self):
        pckt, task = self.makeInputs(
            variables=(((1, 2, 6, 7), "foo"),),
            oidMap={"1.2.6.7": "testVar"}
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 1)
        self.assertIn("testVar", result)
        self.assertEqual(result["testVar"], "foo")

    def test_NamedVarBindMultiValue(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 7), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 7), "baz"),
            ),
            oidMap={"1.2.6.7": "testVar"}
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 1)
        self.assertIn("testVar", result)
        self.assertEqual(result["testVar"], "foo,bar,baz")

    def test_PartialNamedVarBindOneValue(self):
        pckt, task = self.makeInputs(
            variables=(((1, 2, 6, 7), "foo"),),
            oidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("testVar.7", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.7"], "foo")
        self.assertEqual(result["testVar.sequence"], "7")

    def test_PartialNamedVarBindMultiValue(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 7), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 7), "baz"),
            ),
            oidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("testVar.7", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.7"], "foo,bar,baz")
        self.assertEqual(result["testVar.sequence"], "7,7,7")

    def test_PartialNamedMultiVarBind(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 0), "foo"),
                ((1, 2, 6, 1), "bar"),
                ((1, 2, 6, 2), "baz"),
            ),
            oidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 4)
        self.assertIn("testVar.0", result)
        self.assertIn("testVar.1", result)
        self.assertIn("testVar.2", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.0"], "foo")
        self.assertEqual(result["testVar.1"], "bar")
        self.assertEqual(result["testVar.2"], "baz")
        self.assertEqual(result["testVar.sequence"], "0,1,2")

    def test_PartialNamedVarBindNoneValue(self):
        pckt, task = self.makeInputs(
            variables=(((1, 2, 6, 0), None),),
            oidMap={"1.2.6.0": "testVar"}
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 1)
        self.assertIn("testVar", result)
        self.assertEqual(result["testVar"], "None")

    def test_PartialNamedMultiVarBindOrder(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 0), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 3), "baz"),
            ),
            oidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 4)
        self.assertIn("testVar.0", result)
        self.assertIn("testVar.7", result)
        self.assertIn("testVar.3", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.0"], "foo")
        self.assertEqual(result["testVar.7"], "bar")
        self.assertEqual(result["testVar.3"], "baz")
        self.assertEqual(result["testVar.sequence"], "0,7,3")

    def test_ifentry_trap(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 1, 143), 143),
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 7, 143), 2),
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 8, 143), 2),
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 2, 143), "F23"),
                ((1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 143), ""),
            ),
            oidMap={
                "1.3.6.1.2.1.2.2.1.1": "ifIndex",
                "1.3.6.1.2.1.2.2.1.7": "ifAdminStatus",
                "1.3.6.1.2.1.2.2.1.8": "ifOperStatus",
                "1.3.6.1.2.1.2.2.1.2": "ifDescr",
                "1.3.6.1.2.1.31.1.1.1.18": "ifAlias",
            }
        )
        eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)

        totalVarKeys = sum(1 for k in result if k.startswith("ifIndex"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifIndex.143", result)
        self.assertIn("ifIndex.sequence", result)
        self.assertEqual(result["ifIndex.143"], "143")
        self.assertEqual(result["ifIndex.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifAdminStatus"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifAdminStatus.143", result)
        self.assertIn("ifAdminStatus.sequence", result)
        self.assertEqual(result["ifAdminStatus.143"], "2")
        self.assertEqual(result["ifAdminStatus.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifOperStatus"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifOperStatus.143", result)
        self.assertIn("ifOperStatus.sequence", result)
        self.assertEqual(result["ifOperStatus.143"], "2")
        self.assertEqual(result["ifOperStatus.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifDescr"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifDescr.143", result)
        self.assertIn("ifDescr.sequence", result)
        self.assertEqual(result["ifDescr.143"], "F23")
        self.assertEqual(result["ifDescr.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifAlias"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifAlias.143", result)
        self.assertIn("ifAlias.sequence", result)
        self.assertEqual(result["ifAlias.143"], "")
        self.assertEqual(result["ifAlias.sequence"], "143")


class TestDecodeSnmpV2(BaseTestCase):

    baseOidMap = {
        # Std var binds in SnmpV2 traps/notifications
        "1.3.6.1.2.1.1.3": "sysUpTime",
        "1.3.6.1.6.3.1.1.4.1": "snmpTrapOID",

        # SnmpV2 Traps (snmpTrapOID.0 values)
        "1.3.6.1.6.3.1.1.5.1": "coldStart",
        "1.3.6.1.6.3.1.1.5.2": "warmStart",
        "1.3.6.1.6.3.1.1.5.3": "linkDown",
        "1.3.6.1.6.3.1.1.5.4": "linkUp",
        "1.3.6.1.6.3.1.1.5.5": "authenticationFailure",
        "1.3.6.1.6.3.1.1.5.6": "egpNeighborLoss",
    }

    def makePacket(self, trapOID, variables=()):
        pckt = FakePacket()
        pckt.version = SNMPv2
        pckt.host = "localhost"
        pckt.port = 162

        if isinstance(trapOID, (str, unicode)):
            trapOID = tuple(map(int, trapOID.split('.')))
        pckt.variables = [
            ((1, 3, 6, 1, 2, 1, 1, 3, 0), 5342),
            ((1, 3, 6, 1, 6, 3, 1, 1, 4, 1, 0), trapOID)
        ]
        pckt.variables.extend(variables)
        pckt.community = "public"
        pckt.enterprise_length = 0
        return pckt

    def makeTask(self, extraOidMap={}):
        oidMap = self.baseOidMap.copy()
        oidMap.update(extraOidMap)
        return MockTrapTask(oidMap)

    def makeInputs(
            self, trapOID="1.3.6.1.6.3.1.1.5.1", variables=(), extraOidMap={}):
        pckt = self.makePacket(trapOID=trapOID, variables=variables)
        task = self.makeTask(extraOidMap=extraOidMap)
        return pckt, task

    def test_UnknownTrapType(self):
        pckt, task = self.makeInputs(trapOID="1.2.3")
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        self.assertIn("snmpVersion", result)
        self.assertEqual(result["snmpVersion"], "2")
        self.assertEqual(eventType, "1.2.3")
        self.assertIn("snmpVersion", result)
        self.assertIn("oid", result)
        self.assertIn("device", result)
        self.assertEqual(result["snmpVersion"], "2")
        self.assertEqual(result["oid"], "1.2.3")
        self.assertEqual(result["device"], "localhost")

    def test_KnownTrapType(self):
        pckt, task = self.makeInputs(trapOID="1.3.6.1.6.3.1.1.5.1")
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        self.assertIn("oid", result)
        self.assertEqual(eventType, "coldStart")
        self.assertEqual(result["oid"], "1.3.6.1.6.3.1.1.5.1")

    def test_TrapAddressOID(self):
        pckt, task = self.makeInputs(
            trapOID="1.3.6.1.6.3.1.1.5.1",
            variables=(
                ((1, 3, 6, 1, 6, 3, 18, 1, 3), "192.168.51.100"),
            ),
            extraOidMap={
                "1.3.6.1.6.3.18.1.3": "snmpTrapAddress"
            }
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        self.assertIn("snmpTrapAddress", result)
        self.assertEqual(result["snmpTrapAddress"], "192.168.51.100")
        self.assertEqual(result["device"], "192.168.51.100")

    def test_RenamedLinkDown(self):
        pckt, task = self.makeInputs(trapOID="1.3.6.1.6.3.1.1.5.3")
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        self.assertIn("oid", result)
        self.assertEqual(eventType, "snmp_linkDown")
        self.assertEqual(result["oid"], "1.3.6.1.6.3.1.1.5.3")

    def test_RenamedLinkUp(self):
        pckt, task = self.makeInputs(trapOID="1.3.6.1.6.3.1.1.5.4")
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        self.assertIn("oid", result)
        self.assertEqual(eventType, "snmp_linkUp")
        self.assertEqual(result["oid"], "1.3.6.1.6.3.1.1.5.4")

    def test_VarBindMultiValue(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 7), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 7), "baz"),
            )
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        self.assertEqual(result["1.2.6.7"], "foo,bar,baz")

    def test_UnknownMultiVarBind(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 0), "foo"),
                ((1, 2, 6, 1), "bar"),
            )
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("1.2.6.0", result)
        self.assertIn("1.2.6.1", result)
        self.assertEqual(result["1.2.6.0"], "foo")
        self.assertEqual(result["1.2.6.1"], "bar")

    def test_NamedVarBindOneValue(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 7), "foo"),
            ),
            extraOidMap={"1.2.6.7": "testVar"}
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 1)
        self.assertIn("testVar", result)
        self.assertEqual(result["testVar"], "foo")

    def test_NamedVarBindMultiValue(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 7), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 7), "baz"),
            ),
            extraOidMap={"1.2.6.7": "testVar"}
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 1)
        self.assertIn("testVar", result)
        self.assertEqual(result["testVar"], "foo,bar,baz")

    def test_PartialNamedVarBindOneValue(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 7), "foo"),
            ),
            extraOidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("testVar.7", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.7"], "foo")
        self.assertEqual(result["testVar.sequence"], "7")

    def test_PartialNamedVarBindMultiValue(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 7), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 7), "baz"),
            ),
            extraOidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("testVar.7", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.7"], "foo,bar,baz")
        self.assertEqual(result["testVar.sequence"], "7,7,7")

    def test_PartialNamedMultiVarBind(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 0), "foo"),
                ((1, 2, 6, 1), "bar"),
                ((1, 2, 6, 2), "baz"),
            ),
            extraOidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 4)
        self.assertIn("testVar.0", result)
        self.assertIn("testVar.1", result)
        self.assertIn("testVar.2", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.0"], "foo")
        self.assertEqual(result["testVar.1"], "bar")
        self.assertEqual(result["testVar.2"], "baz")
        self.assertEqual(result["testVar.sequence"], "0,1,2")

    def test_PartialNamedVarBindNoneValue(self):
        pckt = self.makePacket("1.3.6.1.6.3.1.1.5.3")
        pckt.variables.append(
            ((1, 2, 6, 0), None),
        )
        task = MockTrapTask({"1.2.6.0": "testVar"})
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 1)
        self.assertIn("testVar", result)
        self.assertEqual(result["testVar"], "None")

    def test_PartialNamedMultiVarBindOrder(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 2, 6, 0), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 3), "baz"),
            ),
            extraOidMap={"1.2.6": "testVar"}
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
        totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
        self.assertEqual(totalVarKeys, 4)
        self.assertIn("testVar.0", result)
        self.assertIn("testVar.7", result)
        self.assertIn("testVar.3", result)
        self.assertIn("testVar.sequence", result)
        self.assertEqual(result["testVar.0"], "foo")
        self.assertEqual(result["testVar.7"], "bar")
        self.assertEqual(result["testVar.3"], "baz")
        self.assertEqual(result["testVar.sequence"], "0,7,3")

    def test_ifentry_trap(self):
        pckt, task = self.makeInputs(
            variables=(
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 1, 143), 143),
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 7, 143), 2),
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 8, 143), 2),
                ((1, 3, 6, 1, 2, 1, 2, 2, 1, 2, 143), "F23"),
                ((1, 3, 6, 1, 2, 1, 31, 1, 1, 1, 18, 143), ""),
            ),
            extraOidMap={
                "1.3.6.1.2.1.2.2.1.1": "ifIndex",
                "1.3.6.1.2.1.2.2.1.7": "ifAdminStatus",
                "1.3.6.1.2.1.2.2.1.8": "ifOperStatus",
                "1.3.6.1.2.1.2.2.1.2": "ifDescr",
                "1.3.6.1.2.1.31.1.1.1.18": "ifAlias",
            }
        )
        eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)

        totalVarKeys = sum(1 for k in result if k.startswith("ifIndex"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifIndex.143", result)
        self.assertIn("ifIndex.sequence", result)
        self.assertEqual(result["ifIndex.143"], "143")
        self.assertEqual(result["ifIndex.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifAdminStatus"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifAdminStatus.143", result)
        self.assertIn("ifAdminStatus.sequence", result)
        self.assertEqual(result["ifAdminStatus.143"], "2")
        self.assertEqual(result["ifAdminStatus.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifOperStatus"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifOperStatus.143", result)
        self.assertIn("ifOperStatus.sequence", result)
        self.assertEqual(result["ifOperStatus.143"], "2")
        self.assertEqual(result["ifOperStatus.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifDescr"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifDescr.143", result)
        self.assertIn("ifDescr.sequence", result)
        self.assertEqual(result["ifDescr.143"], "F23")
        self.assertEqual(result["ifDescr.sequence"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifAlias"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifAlias.143", result)
        self.assertIn("ifAlias.sequence", result)
        self.assertEqual(result["ifAlias.143"], "")
        self.assertEqual(result["ifAlias.sequence"], "143")


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(DecodersUnitTest))
    suite.addTest(makeSuite(TestOid2Name))
    suite.addTest(makeSuite(TestDecodeSnmpV1))
    suite.addTest(makeSuite(TestDecodeSnmpV2))
    return suite
