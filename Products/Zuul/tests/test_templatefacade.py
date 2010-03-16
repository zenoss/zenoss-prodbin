
###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import unittest
from Products import Zuul
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class TemplateFacadeTest(BaseTestCase):

    def setUp(self):
        super(TemplateFacadeTest, self).setUp()
        self.facade = Zuul.getFacade('template', self.dmd)
        #  uid for a template
        self.uid = '/zport/dmd/Devices/rrdTemplates/test1'
        devices = self.dmd.Devices
        devices.manage_addRRDTemplate('test1')
        self.template = self.dmd.unrestrictedTraverse(self.uid)
        
    def _createDummyThreshold(self):
        """
        Creates the test threshold used by the other
        unit tests
        """
        # add the specific threshold
        thresholdType = 'MinMaxThreshold'
        thresholdId = 'test_1'
        dataPoints = []
        self.facade.addThreshold(self.uid,
                                 thresholdType,
                                 thresholdId,
                                 dataPoints)
        thresholds = self.facade.getThresholds(self.uid)
        return thresholds.next()

    def _createDummyDataSource(self):
        """
        Used by multiple unit tests creates a new datasource
        from scratch
        """
        # need the actual template
        template = self.template
        dsOptions = template.getDataSourceOptions()
        datasource = template.manage_addRRDDataSource('testDataSource',
                                                      dsOptions[0][1])
        datasource.sourcetype = 'COMMAND'
        return datasource

    def _createDummyDataPoint(self):
        """
        returns a newly created dummy datapoint
        """
        source = self._createDummyDataSource()
        return source.manage_addRRDDataPoint('testDataPoint')
    
    def testCanAddThreshold(self):
        """ Verify that we can add a dummy threshold
        """
        threshold = self._createDummyThreshold()
        self.assertTrue(threshold)
        
    def testCanGetThresholdDetails(self):
        """
        Unit test for retrieving the information about a threshold. This will need
        to take into account the threshold type
        """
        threshold = self._createDummyThreshold()
        details = self.facade.getThresholdDetails(threshold.id)
        
        # all of the fields we should be returning
        self.assertTrue(details)
        self.assertTrue(details.name)
        self.assertTrue(details.severity)

    def testCanEditThresholdDetails(self):
        """
        Make sure we can always save the threshold (for this case of MinMax)
        """
        data ={'maxval': '123', 'severity': 'Warning', 'minval': '12',
               'escalateCount': '0', 'enabled': 'on',
               'dsnames': 'sysUpTime_sysUpTime', 'eventClass': '/Perf/Snmp'};
        threshold = self._createDummyThreshold()
        result = self.facade.setInfo(threshold.id, data);
        # the values should match the data above
        self.assertEquals(result.maxval, '123');
        self.assertEquals(result.minval, '12');
        self.assertEquals(result.severity, 'Warning');
        self.assertTrue('uptime' in result.dataPoints.lower());
        
    def testCanCreateDataSource(self):
        """
        Make sure we can create a DataSource, this will be used by the
        making sure we can delete and edit datasources unit tests
        """
        datasource = self._createDummyDataSource()
        self.assertTrue(datasource, "We actually created the datasource object")

    def testCanEditDataSource(self):
        """
        Make sure when we edit a datasource the values stay
        """
        data ={'enabled': True, 'severity': 'Warning', 'eventClass': '/Perf/Snmp'}
        datasource = self._createDummyDataSource()
        info = self.facade.getDataSourceDetails(datasource.absolute_url_path())
        self.assertTrue(info, "make sure we can create an info from a datasource")
        newInfo = self.facade.setInfo(info.id, data)
        # since we saved it, make sure the values stick
        self.assertEqual(newInfo.enabled, True)
        self.assertEqual(newInfo.severity, data['severity'])
        self.assertEqual(newInfo.eventClass, data['eventClass'])
        
    def testCanEditDataPointDetails(self):
        data = {'createCmd': 'foobar', 'rrdmin': 'foo', 'rrdmax': 'bar', 'isrow': False}
        datapoint = self._createDummyDataPoint()
        info = self.facade.getDataPointDetails(datapoint.absolute_url_path())
        self.assertTrue(info, "make sure we got the details")
        newInfo = self.facade.setInfo(info.id, data)
        self.assertEqual(newInfo.isrow, data['isrow'])
        self.assertEqual(newInfo.createCmd, data['createCmd'])
        self.assertEqual(newInfo.rrdmin, data['rrdmin'])
        
def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TemplateFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
    
