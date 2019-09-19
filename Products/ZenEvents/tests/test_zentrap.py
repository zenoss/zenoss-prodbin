import base64
import logging

from struct import pack
from unittest import TestCase

from Products.ZenEvents.zentrap import (
    decode_snmp_value, TrapTask, FakePacket, SNMPv1, SNMPv2
)

log = logging.getLogger("test_zentrap")


class DecodersUnitTest(TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

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


class TestOid2Name(TestCase):

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


class _SnmpV1Base(object):

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


class TestDecodeSnmpV1(TestCase, _SnmpV1Base):

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


class _SnmpV2Base(object):

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
        self, trapOID="1.3.6.1.6.3.1.1.5.1", variables=(), oidMap={},
    ):
        pckt = self.makePacket(trapOID=trapOID, variables=variables)
        task = self.makeTask(extraOidMap=oidMap)
        return pckt, task


class TestDecodeSnmpV2(TestCase, _SnmpV2Base):

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
            oidMap={
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


class _VarbindTests(object):

    def case_unknown_id_single(self):
        tests = (
            self.makeInputs(variables=(
                ((1, 2, 6, 7), "foo"),
            )),
        )
        for test in tests:
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
            self.assertEqual(totalVarKeys, 1)
            self.assertEqual(result["1.2.6.7"], "foo")

    def case_unknown_id_repeated(self):
        tests = (
            self.makeInputs(variables=(
                ((1, 2, 6, 7), "foo"),
                ((1, 2, 6, 7), "bar"),
                ((1, 2, 6, 7), "baz"),
            )),
        )
        for test in tests:
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
            self.assertEqual(totalVarKeys, 1)
            self.assertEqual(result["1.2.6.7"], "foo,bar,baz")

    def case_unknown_ids_multiple(self):
        tests = (
            self.makeInputs(variables=(
                ((1, 2, 6, 0), "foo"),
                ((1, 2, 6, 1), "bar"),
            )),
        )
        expected_results = ({
            "1.2.6.0": "foo",
            "1.2.6.1": "bar",
        },)
        for test, expected in zip(tests, expected_results):
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            totalVarKeys = sum(1 for k in result if k.startswith("1.2.6"))
            self.assertEqual(totalVarKeys, 2)
            for key, value in expected.items():
                self.assertIn(key, result)
                self.assertEqual(value, result[key])

    def case_one_id(self):
        tests = (
            self.makeInputs(
                variables=(((1, 2, 6, 7), "foo"),),
                oidMap={"1.2.6.7": "testVar"}
            ),
        )
        expected_results = ({
            "testVar": "foo",
        },)
        for test, expected in zip(tests, expected_results):
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            totalVarKeys = sum(1 for k in result if k.startswith("testVar"))
            self.assertEqual(totalVarKeys, 1)
            for key, value in expected.items():
                self.assertIn(key, result)
                self.assertEqual(value, result[key])

    def case_one_id_one_sub_id(self):
        oidMap = {"1.2.6": "testVar"}
        tests = (
            self.makeInputs(
                variables=(((1, 2, 6, 0), "foo"),), oidMap=oidMap,
            ),
            self.makeInputs(
                variables=(((1, 2, 6, 5), "foo"),), oidMap=oidMap,
            ),
        )
        expected_results = ({
            "testVar": "foo",
            "testVar.ifIndex": "0",
        }, {
            "testVar": "foo",
            "testVar.ifIndex": "5",
        },)
        for test, expected in zip(tests, expected_results):
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            count = sum(1 for k in result if k.startswith("testVar"))
            self.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                self.assertIn(key, result)
                self.assertEqual(value, result[key])

    def case_one_id_multiple_sub_ids(self):
        oidMap = {"1.2.6": "testVar"}
        tests = (
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 0), "foo"),
                    ((1, 2, 6, 1), "bar"),
                    ((1, 2, 6, 2), "baz"),
                ), oidMap=oidMap,
            ),
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 7), "foo"),
                    ((1, 2, 6, 2), "bar"),
                ), oidMap=oidMap,
            ),
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 3), "foo"),
                    ((1, 2, 6, 3), "bar"),
                ), oidMap=oidMap,
            ),
        )
        expected_results = ({
            "testVar.0": "foo",
            "testVar.1": "bar",
            "testVar.2": "baz",
            "testVar.sequence": "0,1,2",
        }, {
            "testVar.7": "foo",
            "testVar.2": "bar",
            "testVar.sequence": "7,2",
        }, {
            "testVar.3": "foo,bar",
            "testVar.sequence": "3,3",
        })
        for test, expected in zip(tests, expected_results):
            result = yield test
            count = sum(1 for k in result if k.startswith("testVar"))
            self.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                self.assertIn(key, result)
                self.assertEqual(value, result[key])

    def case_multiple_ids(self):
        oidMap = {
            "1.2.6": "foo",
            "1.2.7": "bar",
        }
        tests = (
            self.makeInputs(
                variables=(
                    ((1, 2, 6), "is a foo"),
                    ((1, 2, 7), "lower the bar"),
                ), oidMap=oidMap,
            ),
        )
        expected_results = ({
            "foo": "is a foo",
            "bar": "lower the bar",
        },)
        for test, expected in zip(tests, expected_results):
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            count = sum(
                1 for k in result
                if k.startswith("bar") or k.startswith("foo")
            )
            self.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                self.assertIn(key, result)
                self.assertEqual(value, result[key])

    def case_multiple_ids_one_sub_id_each(self):
        oidMap = {
            "1.2.6": "foo",
            "1.2.7": "bar",
        }
        tests = (
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 0), "is a foo"),
                    ((1, 2, 7, 2), "lower the bar"),
                ), oidMap=oidMap,
            ),
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 0, 1), "is a foo"),
                    ((1, 2, 7, 2, 1), "lower the bar"),
                ), oidMap=oidMap,
            ),
        )
        expected_results = ({
            "foo": "is a foo",
            "foo.ifIndex": "0",
            "bar": "lower the bar",
            "bar.ifIndex": "2",
        }, {
            "foo": "is a foo",
            "foo.ifIndex": "0.1",
            "bar": "lower the bar",
            "bar.ifIndex": "2.1",
        },)
        for test, expected in zip(tests, expected_results):
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            count = sum(
                1 for k in result
                if k.startswith("bar") or k.startswith("foo")
            )
            self.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                self.assertIn(key, result)
                self.assertEqual(value, result[key])

    def case_multiple_ids_multiple_sub_ids(self):
        oidMap = {
            "1.2.6": "foo",
            "1.2.7": "bar",
        }
        tests = (
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 0), "here a foo"),
                    ((1, 2, 6, 1), "there a foo"),
                    ((1, 2, 7, 2), "lower the bar"),
                    ((1, 2, 7, 4), "raise the bar"),
                ), oidMap=oidMap,
            ),
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 0, 1), "here a foo"),
                    ((1, 2, 6, 1, 1), "there a foo"),
                    ((1, 2, 7, 2, 1), "lower the bar"),
                    ((1, 2, 7, 2, 2), "raise the bar"),
                ), oidMap=oidMap,
            ),
            self.makeInputs(
                variables=(
                    ((1, 2, 6, 0), "here a foo"),
                    ((1, 2, 6, 0), "there a foo"),
                    ((1, 2, 7, 3), "lower the bar"),
                    ((1, 2, 7, 3), "raise the bar"),
                ), oidMap=oidMap,
            ),
        )
        expected_results = ({
            "foo.0": "here a foo",
            "foo.1": "there a foo",
            "foo.sequence": "0,1",
            "bar.2": "lower the bar",
            "bar.4": "raise the bar",
            "bar.sequence": "2,4",
        }, {
            "foo.0.1": "here a foo",
            "foo.1.1": "there a foo",
            "foo.sequence": "0.1,1.1",
            "bar.2.1": "lower the bar",
            "bar.2.2": "raise the bar",
            "bar.sequence": "2.1,2.2",
        }, {
            "foo.0": "here a foo,there a foo",
            "foo.sequence": "0,0",
            "bar.3": "lower the bar,raise the bar",
            "bar.sequence": "3,3",
        },)
        for test, expected in zip(tests, expected_results):
            result = yield test
            # eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
            count = sum(
                1 for k in result
                if k.startswith("bar") or k.startswith("foo")
            )
            self.assertEqual(count, len(expected.keys()))
            for key, value in expected.items():
                self.assertIn(key, result)
                self.assertEqual(value, result[key])

    def case_ifentry_trap(self):
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

        result = yield (pckt, task)

        totalVarKeys = sum(1 for k in result if k.startswith("ifIndex"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifIndex", result)
        self.assertIn("ifIndex.ifIndex", result)
        self.assertEqual(result["ifIndex"], "143")
        self.assertEqual(result["ifIndex.ifIndex"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifAdminStatus"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifAdminStatus", result)
        self.assertIn("ifAdminStatus.ifIndex", result)
        self.assertEqual(result["ifAdminStatus"], "2")
        self.assertEqual(result["ifAdminStatus.ifIndex"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifOperStatus"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifOperStatus", result)
        self.assertIn("ifOperStatus.ifIndex", result)
        self.assertEqual(result["ifOperStatus"], "2")
        self.assertEqual(result["ifOperStatus.ifIndex"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifDescr"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifDescr", result)
        self.assertIn("ifDescr.ifIndex", result)
        self.assertEqual(result["ifDescr"], "F23")
        self.assertEqual(result["ifDescr.ifIndex"], "143")

        totalVarKeys = sum(1 for k in result if k.startswith("ifAlias"))
        self.assertEqual(totalVarKeys, 2)
        self.assertIn("ifAlias", result)
        self.assertIn("ifAlias.ifIndex", result)
        self.assertEqual(result["ifAlias"], "")
        self.assertEqual(result["ifAlias.ifIndex"], "143")


class TestSnmpV1VarbindHandling(TestCase, _SnmpV1Base, _VarbindTests):

    def _execute(self, cases):
        try:
            pckt, task = next(cases)
            while True:
                eventType, result = task.decodeSnmpv1(("localhost", 162), pckt)
                pckt, task = cases.send(result)
        except StopIteration:
            pass

    def test_unknown_id_single(self):
        self._execute(self.case_unknown_id_single())

    def test_unknown_id_repeated(self):
        self._execute(self.case_unknown_id_repeated())

    def test_unknown_ids_multiple(self):
        self._execute(self.case_unknown_ids_multiple())

    def test_one_id(self):
        self._execute(self.case_one_id())

    def test_one_id_one_sub_id(self):
        self._execute(self.case_one_id_one_sub_id())

    def test_one_id_multiple_sub_ids(self):
        self._execute(self.case_one_id_multiple_sub_ids())

    def test_multiple_ids(self):
        self._execute(self.case_multiple_ids())

    def test_multiple_ids_one_sub_id_each(self):
        self._execute(self.case_multiple_ids_one_sub_id_each())

    def test_multiple_ids_multiple_sub_ids(self):
        self._execute(self.case_multiple_ids_multiple_sub_ids())

    def test_ifentry_trap(self):
        self._execute(self.case_ifentry_trap())


class TestSnmpV2VarbindHandling(TestCase, _SnmpV2Base, _VarbindTests):

    def _execute(self, cases):
        try:
            pckt, task = next(cases)
            while True:
                eventType, result = task.decodeSnmpv2(("localhost", 162), pckt)
                pckt, task = cases.send(result)
        except StopIteration:
            pass

    def test_unknown_id_single(self):
        self._execute(self.case_unknown_id_single())

    def test_unknown_id_repeated(self):
        self._execute(self.case_unknown_id_repeated())

    def test_unknown_ids_multiple(self):
        self._execute(self.case_unknown_ids_multiple())

    def test_one_id(self):
        self._execute(self.case_one_id())

    def test_one_id_one_sub_id(self):
        self._execute(self.case_one_id_one_sub_id())

    def test_one_id_multiple_sub_ids(self):
        self._execute(self.case_one_id_multiple_sub_ids())

    def test_multiple_ids(self):
        self._execute(self.case_multiple_ids())

    def test_multiple_ids_one_sub_id_each(self):
        self._execute(self.case_multiple_ids_one_sub_id_each())

    def test_multiple_ids_multiple_sub_ids(self):
        self._execute(self.case_multiple_ids_multiple_sub_ids())

    def test_ifentry_trap(self):
        self._execute(self.case_ifentry_trap())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(DecodersUnitTest))
    suite.addTest(makeSuite(TestOid2Name))
    suite.addTest(makeSuite(TestDecodeSnmpV1))
    suite.addTest(makeSuite(TestDecodeSnmpV2))
    suite.addTest(makeSuite(TestSnmpV1VarbindHandling))
    suite.addTest(makeSuite(TestSnmpV2VarbindHandling))
    return suite
