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

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BasePublisherTestCase))
    suite.addTest(unittest.makeSuite(HttpPostPublisherTestCase))
    suite.addTest(unittest.makeSuite(RedisPublisherTestCase))
    return suite
