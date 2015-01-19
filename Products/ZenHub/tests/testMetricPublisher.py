##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest

import ujson as json

from Products.ZenHub.metricpublisher.publisher import RedisListPublisher, HttpPostPublisher, BasePublisher
from Products.ZenHub.metricpublisher.utils import sanitized_float


class BasePublisherTestCase(unittest.TestCase):
    def testBuildMetric(self):
        publisher = BasePublisher(0, 0)
        self.assertEquals(
                {'metric':'m', 'value':1.0, 'timestamp':1, 'tags':{}},
                publisher.build_metric( 'm', 1.0, 1, {}))
        self.assertEquals(
                {'metric':'m', 'value':1.0, 'timestamp':1, 'tags':{}},
                publisher.build_metric( 'm', "1.0", 1, {}))

class HttpPostPublisherTestCase(unittest.TestCase):
    def testPut(self):
        publisher = HttpPostPublisher(None,None)
        publisher.put( 'm', '1.0', 1, {})
        publisher.put( 'm', 1.0, 1, {})
        self.assertEquals( 2, len(publisher._mq))
        self.assertEquals(
                {"metric":"m", "value":1.0, "timestamp":1, "tags":{}},
                publisher._mq.pop())
        self.assertEquals(
                {"metric":"m", "value":1.0, "timestamp":1, "tags":{}},
                publisher._mq.pop())

class RedisPublisherTestCase(unittest.TestCase):
    def testPut(self):
        publisher = RedisListPublisher()
        publisher.put( 'm', '0', 1, {})
        publisher.put( 'm', 0, 1, {})
        self.assertEquals( 2, len(publisher._mq))
        self.assertEquals(
                json.dumps({"metric":"m","value":0.0,"timestamp":1,"tags":{}}),
                publisher._mq.pop())
        self.assertEquals(
                json.dumps({"metric":"m","value":0.0,"timestamp":1,"tags":{}}),
                publisher._mq.pop())


class UtilsTestCase(unittest.TestCase):
    def test_sanitized_float(self):
        # The result of float() and sanitized_float() should match for
        # these.
        float_inputs = [
            100, '100', u'100',
            -100, '-100', u'-100',
            100.1, '100.1', u'100.1',
            -100.1, '-100.1', u'-100.1',
            1e9, '1e9', u'1e9',
            -1e9, '-1e9', u'-1e9',
            1.1e9, '1.1e9', u'1.1e9',
            -1.1e9, '-1.1e9', u'-1.1e9'
            ]

        for value in float_inputs:
            self.assertEquals(sanitized_float(value), float(value))

        # First item in tuple should be normalized to second item.
        normalized_inputs = [
            ('100%', 100.0),
            ('-100%', -100.0),
            ('100.1%', 100.1),
            ('-100.1%', -100.1),
            ('123 V', 123.0),
            ('F123', 123.0),
            ]

        for value, expected_output in normalized_inputs:
            self.assertEquals(sanitized_float(value), expected_output)

        # Bad inputs should result in None.
        bad_inputs = [
            'not-applicable',
            ]

        for value in bad_inputs:
            self.assertEquals(sanitized_float(value), None)

        # make sure we can read exponential values if they have a capital E
        self.assertEqual(sanitized_float("3.33333333333333E-5"), float("3.33333333333333E-5"))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BasePublisherTestCase))
    suite.addTest(unittest.makeSuite(HttpPostPublisherTestCase))
    suite.addTest(unittest.makeSuite(RedisPublisherTestCase))
    suite.addTest(unittest.makeSuite(UtilsTestCase))
    return suite
