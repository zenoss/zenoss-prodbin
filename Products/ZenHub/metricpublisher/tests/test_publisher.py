##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import unittest
from mock import Mock, create_autospec, patch, call

import ujson as json

from Products.ZenHub.metricpublisher.publisher import RedisListPublisher, HttpPostPublisher, BasePublisher, deque, bufferHighWater, defer
from Products.ZenHub.metricpublisher.utils import sanitized_float


METRIC_BUILDED = ['{"timestamp":1535460634.26479,"metric":"eventQueueLength","value":0.0,"tags":{"instance":"0","daemon":"zenpython","monitor":"localhost","metricType":"GAUGE","tenantId":"b0e4t72hrole5z1xv88djc1hb"}}']
METRIC = 'testMetricName'
BUFFER_LEN = 10
PUBLISHER_FREQ = 10
SCHEDULED = True

class PublishError(Exception):
    def __init__(self):
        super(PublishError, self).__init__("Some error in publishing")

class BasePublisherTestCase(unittest.TestCase):

    def setUp(self):
        self.pub = BasePublisher(BUFFER_LEN, PUBLISHER_FREQ)

    def test_init(self):
        metric_queue = deque(maxlen=BUFFER_LEN)
        tagsToFilter = ('internal',)
        publisher = BasePublisher(BUFFER_LEN, PUBLISHER_FREQ)
        self.assertEqual(publisher._buflen, BUFFER_LEN)
        self.assertEqual(publisher._pubfreq, PUBLISHER_FREQ)
        self.assertEqual(publisher._pubtask, None)
        self.assertEqual(publisher._tagsToFilter, tagsToFilter)

    def test_build_metric(self):
        self.assertEquals(
                {'metric':'m', 'value':1.0, 'timestamp':1, 'tags':{}},
                self.pub.build_metric( 'm', 1.0, 1, {}))
        self.assertEquals(
                {'metric':'m', 'value':1.0, 'timestamp':1, 'tags':{}},
                self.pub.build_metric( 'm', "1.0", 1, {}))

    def test_publish_failed(self):
        pub_error = PublishError()
        self.pub._publish_failed(pub_error, METRIC_BUILDED)
        #TODO figured out with maxlen
        self.assertEqual(len(self.pub._mq), len(METRIC_BUILDED))

    def test_reschedule_pubtask(self):
        self.pub._reschedule_pubtask(scheduled=True)
        # check if we created new task
        self.assertTrue(self.pub._pubtask)

    def test_reschedule_pubtask_cancel(self):
        self.pub._reschedule_pubtask(scheduled=True)
        canceled_task = self.pub._pubtask
        # check if we canceled the previous task
        self.pub._reschedule_pubtask(scheduled=False)
        cancel_flag = 1
        self.assertEqual(canceled_task.cancelled, cancel_flag)

    def test_put_not_impl(self):
        with self.assertRaises(NotImplementedError):
            self.pub._put(scheduled=False)

    def test_put(self):
        self.pub.build_metric = create_autospec(self.pub.build_metric, return_value=METRIC_BUILDED)
        result = self.pub.put(METRIC, value=1, timestamp=123.4, tags={})
        self.assertIsInstance(result, defer.Deferred)
        self.assertEqual(len(self.pub._mq), len(METRIC_BUILDED))

    def test_putLater(self):
        self.pub._put = create_autospec(self.pub._put)
        


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
