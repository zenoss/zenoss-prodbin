###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################
import os, sys, unittest
from Products.ZenModel.ValueChangeThreshold import ValueChangeThresholdInstance
from Products.ZenUtils.mock import MockObject

if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))



class TestValueChangeThreshold(unittest.TestCase):
    def testImpl(self):
        mKey=MockObject(return__="testKey")
        context = MockObject(key=mKey)
        threshold = ValueChangeThresholdInstance("testThrehold",context,'','/Status/Perf', 4)
        events = threshold._checkImpl("testDataPoint", 1.0)
        self.assertIsNotNone(events)
        self.assertEquals(1,len(events))
        event = events[0]
        self.assertEquals(1.0, event['current'])
        self.assertEquals(None, event['previous'])
        self.assertEquals('testThrehold', event['eventKey'])
        self.assertEquals(4, event['severity'])
        self.assertEquals('/Status/Perf', event['eventClass'])

        events = threshold._checkImpl("testDataPoint", 1.0)
        self.assertIsNotNone(events)
        self.assertEquals(0,len(events))

        events = threshold._checkImpl("testDataPoint", 2.0)
        self.assertIsNotNone(events)
        self.assertEquals(1,len(events))
        event = events[0]
        self.assertEquals(2.0, event['current'])
        self.assertEquals(1.0   , event['previous'])
        self.assertEquals('testThrehold', event['eventKey'])
        self.assertEquals(4, event['severity'])
        self.assertEquals('/Status/Perf', event['eventClass'])



def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestValueChangeThreshold))
    return suite


