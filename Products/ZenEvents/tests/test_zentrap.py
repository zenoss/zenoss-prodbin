from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenEvents.zentrap import decode_snmp_value

from struct import pack


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


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(DecodersUnitTest))
    return suite
