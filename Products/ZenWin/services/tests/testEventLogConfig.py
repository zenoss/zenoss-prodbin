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

import Globals

from Products.ZenModel.Device import Device, manage_createDevice
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenWin.services.EventLogConfig import EventLogConfig

class TestEventLogConfig(ZenModelBaseTest):
    def setUp(self):
        super(TestEventLogConfig, self).setUp()
        dev = manage_createDevice(self.dmd, "test-dev1",
                                  "/Server/Windows",
                                  manageIp="10.0.10.1")
        dev.zWmiMonitorIgnore = False
        dev.zWinEventlog = True
        self._testDev = dev
        self._deviceNames = [ "test-dev1" ]
        self._configService = EventLogConfig(self.dmd, "localhost")

    def tearDown(self):
        super(TestEventLogConfig, self).tearDown()
        self._testDev = None
        self._deviceNames = None
        self._configService = None

    def testProductionStateFilter(self):
        self._testDev.setProdState(-1)

        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 0)

        self._testDev.setProdState(1000)
        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 1)

    def testWmiMonitorFlagFilter(self):
        self._testDev.zWmiMonitorIgnore = True
        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 0)

        self._testDev.zWmiMonitorIgnore = False
        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 1)

    def testEventLogFlagFilter(self):
        self._testDev.zWinEventlog = False
        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 0)

        self._testDev.zWinEventlog = True
        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 1)

    def testMultipleDevices(self):
        dev = manage_createDevice(self.dmd, "test-dev2",
                                  "/Server/Windows",
                                  manageIp="10.0.10.2")
        dev.zWmiMonitorIgnore = False
        dev.zWinEventlog = True
        self._deviceNames.append("test-dev2")

        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertTrue(len(proxies), 2)

        proxies = self._configService.remote_getDeviceConfigs(None)
        self.assertTrue(len(proxies), 2)

    def testMultipleDevicesWithDuplicate(self):
        dev = manage_createDevice(self.dmd, "test-dev2",
                                  "/Server/Windows",
                                  manageIp="10.0.10.2")
        dev.zWmiMonitorIgnore = False
        dev.zWinEventlog = True
        dev.setManageIp("10.0.10.1")

        proxies = self._configService.remote_getDeviceConfigs()
        self.assertEqual(len(proxies), 1)

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestEventLogConfig))
    return suite

if __name__=="__main__":
    framework()
