###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009 Zenoss Inc.
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

import Globals

from Products.ZenCollector.services.config import CollectorConfigService
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class TestCollectorConfig(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)

        self._devices = []

        device = self.dmd.Devices.createInstance("testdev1")
        device.zFoobar = True
        self._devices.append(device)

        device = self.dmd.Devices.createInstance("testdev2")
        device.zFoobar = False
        self._devices.append(device)

        device = self.dmd.Devices.createInstance("testdev3")
        self._devices.append(device)

    def tearDown(self):
        pass

    def testFilter(self):
        class MyCollectorConfig(CollectorConfigService):
            def __init__(self):
                attrs = ('zFooBar', 'zWoot')
                CollectorConfigService.__init__(self, self.dmd, "localhost", attrs)

            def _filterDevice(self, device):
                return getattr(device, 'zFooBar', False)

        config = MyCollectorConfig()
        
        self.assertTrue(False)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestCollectorConfig))
    return suite

if __name__=="__main__":
    framework()
