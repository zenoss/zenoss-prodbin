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

import os, sys, time

from DateTime import DateTime

from Products.ZenModel.Exceptions import *
from Products.ZenModel.Device import Device, manage_createDevice
from Products.ZenModel.tests.ZenModelBaseTest import ZenModelBaseTest
from Products.ZenWin.services.WmiConfig import WmiConfig


class TestWmiConfig(ZenModelBaseTest):

    def testRemote_getDeviceConfigAndWinServices(self):
        """
        Tests fetching set of device proxies remotely when devices with 
        duplicates mananageIp's exist in the dmd.
        """
        # create a bad scenario where two devices share the same manageIp
        dev = manage_createDevice(self.dmd, 'wmiconfigtest-dev1', 
                                  '/Server/Windows', manageIp='10.10.10.2')
        dev.zWmiMonitorIgnore = False
        dev.zWinEventlog = True
        dev2 = manage_createDevice(self.dmd, '10.10.10.1', 
                                   '/Server/Windows', manageIp='10.10.10.1')
        dev2.zWmiMonitorIgnore = False
        dev2.zWinEventlog = True

        dev.setManageIp('10.10.10.1')

        wmiConfig = WmiConfig(self.dmd, 'localhost')
        names = ['wmiconfigtest-dev1', '10.10.10.1']
        proxies = wmiConfig.remote_getDeviceConfigAndWinServices(names)

        # now validate the right thing happened, which is the multiple
        # devices with the same manageIp did not result in two different
        # device proxies back to the same device
        self.assert_(proxies[0].getId() != proxies[1].getId())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestWmiConfig))
    return suite

if __name__=="__main__":
    framework()

