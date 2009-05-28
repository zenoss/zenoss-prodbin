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
import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

import re
import zlib
from base64 import urlsafe_b64decode

from ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.RRDTemplate import manage_addRRDTemplate


class TestGraphDefinition(ZenModelBaseTest):
    
    def testThresholdGraphPoints(self):
        """
        Test that the correct RRD commands are generated for a number of
        ThresholdGraphPoint configurations.
        """
        device = self.dmd.Devices.createInstance('testdevice')
        device.setPerformanceMonitor('localhost')
        
        manage_addRRDTemplate(device, 'TestTemplate')
        device.bindTemplates(['TestTemplate'])
        template = device.TestTemplate
        
        ds = template.manage_addRRDDataSource('dsname', 'BuiltInDS.Built-In')
        dp = ds.manage_addRRDDataPoint('dpname')
        
        t = template.manage_addRRDThreshold('defaultLegend', 'MinMaxThreshold')
        t.dsnames = ['dsname_dpname']
        t.maxval = '5'
        
        t = template.manage_addRRDThreshold('blankLegend', 'MinMaxThreshold')
        t.dsnames = ['dsname_dpname']
        t.legend = ''
        t.maxval = '10'
        
        t = template.manage_addRRDThreshold('talesLegend', 'MinMaxThreshold')
        t.dsnames = ['dsname_dpname']
        t.legend = '${here/id}'
        t.maxval = '15'
        
        graph = template.manage_addGraphDefinition('graph')
        graph.manage_addDataPointGraphPoints(
            ['dsname_dpname'], includeThresholds=True)
        
        graph.graphPoints.defaultLegend.legend = '${graphPoint/id}'
        graph.graphPoints.blankLegend.legend = ''
        graph.graphPoints.talesLegend.legend = '${here/id}'
        
        graphUrl = device.getDefaultGraphDefs()[0]['url']
        gopts = re.search('gopts=([^&]+)', graphUrl).groups()[0]
        gopts = zlib.decompress(urlsafe_b64decode(gopts))
        self.assertTrue('defaultLegend' in gopts)
        self.assertTrue('dpname > 10' in gopts)
        self.assertTrue('testdevice' in gopts)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestGraphDefinition))
    return suite

if __name__=="__main__":
    framework()
