##############################################################################
#
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


import unittest
from Products import Zuul
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from zenoss.protocols.services import JsonRestServiceClient

class MockRestServiceClient(JsonRestServiceClient):

    def _executeRequest(self, request):
        return 200, '[2]'

class MetricFacadeTest(BaseTestCase):

    def afterSetUp(self):
        super(MetricFacadeTest, self).afterSetUp()
        self.facade = Zuul.getFacade('metric', self.dmd)
        self.facade._client = MockRestServiceClient('http://localhost:8888')

    def testTagBuilder(self):
        dev = self.dmd.Devices.createInstance('device1')
        self.assertTrue(dev.getResourceKey())
        tags = self.facade._buildTagsFromContextAndMetric(dev, 'pepe')
        self.assertIn('key', tags)
        self.assertIn(dev.getResourceKey(), tags['key'])

    def testMetricBuilder(self):
        dev = self.dmd.Devices.createInstance('device1')
        templateFac = Zuul.getFacade('template', self.dmd)
        template = templateFac.addTemplate('test', '/zport/dmd/Devices')._object
        templateFac.addDataSource(template.getPrimaryId(), 'test', 'SNMP')
        metric = template.datasources()[0].datapoints()[0]
        cf = "avg"
        metric = self.facade._buildMetric(dev, metric, cf)
        self.assertEquals(metric['metric'], "device1/test_test")
        self.assertEquals(metric['aggregator'], 'avg')

    def testRequestBuilder(self):
        metric = ["laLoadInt1_laLoadInt1"]
        dev = self.dmd.Devices.createInstance('device1')
        request = self.facade._buildRequest([dev], metric, None, None, "LAST")
        self.assertEquals(request['returnset'], 'LAST')


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(MetricFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
