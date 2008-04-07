###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2008, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import Globals
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenWin import WMIClient
from Products.DataCollector.DeviceProxy import DeviceProxy

import os
import socket
import pywintypes

WMIClient.BaseName = 'test'

class WMIClientTest(WMIClient.WMIClient):

    @WMIClient.watchForFailure
    def test(self, success=True):
        "Test watchForFailure"
        assert WMIClient.failures() == [('win2003.zenoss.loc', 'test'),]
        assert os.path.exists(WMIClient.zenPath('var', 'test', self.name))
        assert success

class TestWMIFail(BaseTestCase):
    def testWmiFail(self):
        cmd = ZCmdBase(noopts=True)
        testPass = cmd.dmd.Devices.Server.Windows.zWinPassword
	if not testPass: return
        WMIClient.failures(clean=True)
        self.assert_(len(WMIClient.failures()) == 0)
        device = DeviceProxy()
        device.id = 'win2003.zenoss.loc'
        device.manageIp = socket.gethostbyname(device.id)
        device.zWinUser = '.\\Administrator'
        device.zWinPassword = testPass
        client = WMIClientTest(device)
        client.connect()
        client.test()
        result = client.query({'q': 'select * from Win32_ComputerSystem'})
        self.assert_(result.has_key('q'))
        try:
            client.test(success=False)
        except AssertionError, ex:
            self.assert_(len(WMIClient.failures()) == 0)
        w = client.watcher()
        try:
            w.nextEvent()
        except pywintypes.com_error:
            pass
        client.close()

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestWMIFail))
    return suite
