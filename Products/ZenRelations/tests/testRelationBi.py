###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
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

from Acquisition import aq_base
from Products.ZenRelations.tests.TestSchema import *
from Products.ZenRelations.Exceptions import *
from Products.ZenRelations.ToOneRelationship import ToOneRelationship

from Products.ZenModel.DeviceClass import DeviceClass
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenModel.PerformanceConf import manage_addPerformanceConf

from Products.ZenRelations.Exceptions import *

import logging
relations_log = logging.getLogger('zen.Relations')
ORIG_LEVEL = relations_log.level

class TestRelationBi(ZenModelBaseTest):

    def setUp(self):
        super(TestRelationBi, self).setUp()
        # Only show greater-than-critical log messages; that is, none
        relations_log.setLevel(100) 
        self.devclass = self.dmd.Devices.createOrganizer('devclass')
        self.dev = self.devclass.createInstance('dev')
        self.dev.setPerformanceMonitor('collector')
        self.collector = self.dmd.Monitors.getPerformanceMonitor('collector')

    def tearDown(self):
        super(TestRelationBi, self).tearDown()
        self.devclass = None
        self.dev = None
        self.collector = None
        relations_log.setLevel(ORIG_LEVEL) 
    
    
    def testToManyCleanup(self):
        """test that to many acces will clean up a to one relation
        """
        self.dev.perfServer._remove()
        self.collector.devices()
        self.assert_(self.collector.devices()[0] == self.dev)
        self.assert_(self.dev.perfServer() == self.collector)
            
    def testToOneCleanup(self):
        """check that a broken to many relation is repaired by to one access
        """
        self.collector.devices._remove(self.dev)
        self.assert_(len(self.collector.devices()) == 0)
        self.dev.perfServer()
        self.assert_(self.collector.devices()[0] == self.dev)
        self.assert_(self.dev.perfServer() == self.collector)
        

    def testToManyDeletedObjectCleanup(self):
        """test that deleted primary path to object is removed on a to many
        """
        self.devclass.devices._remove(self.dev)
        self.assert_(len(self.collector.devices()) == 0)
        


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestRelationBi))
    return suite


if __name__ == '__main__':
    framework()
