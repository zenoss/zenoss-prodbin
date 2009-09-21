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
from Products.ZenModel.WinService import WinService, manage_addWinService
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenWin.services.WinServiceConfig import WinServiceConfig

class TestWinServiceConfig(ZenModelBaseTest):
    def setUp(self):
        super(TestWinServiceConfig, self).setUp()
        dev = manage_createDevice(self.dmd, "test-dev1",
                                  "/Server/Windows",
                                  manageIp="10.0.10.1")
        dev.zWmiMonitorIgnore = False
        winService = manage_addWinService(dev, 'wsvc', 'test service')
        winService.zMonitor = True
        winService.monitor = True
        winService.startMode = 'Auto'
        dev.os.winservices._setObject('wsvc', winService)
        self._testDev = dev
        self._deviceNames = [ "test-dev1" ]
        self._configService = WinServiceConfig(self.dmd, "localhost")

    def tearDown(self):
        super(TestWinServiceConfig, self).tearDown()
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

    def testMultipleDevicesWithDuplicate(self):
        dev = manage_createDevice(self.dmd, "test-dev2",
                                  "/Server/Windows",
                                  manageIp="10.0.10.2")
        dev.setManageIp("10.0.10.1")

        proxies = self._configService.remote_getDeviceConfigs()
        self.assertEqual(len(proxies), 1)

    def testUnmonitoredService(self):
        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 1)

        self._testDev.os.winservices()[0].zMonitor = False
        proxies = self._configService.remote_getDeviceConfigs(self._deviceNames)
        self.assertEqual(len(proxies), 0)


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestWinServiceConfig))
    return suite

if __name__=="__main__":
    framework()
