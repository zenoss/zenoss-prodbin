
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
        self.facade = Zuul.getFacade('template')
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
        result = self.facade.editThreshold(threshold.id, data);
        
        self.assertEquals(result.maxval, '123');
        self.assertEquals(result.minval, '12');
        self.assertEquals(result.severity, 'Warning');
        self.assertTrue('uptime' in result.dataPoints.lower());
        
        
def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TemplateFacadeTest),))


if __name__=="__main__":
    unittest.main(defaultTest='test_suite')
    
