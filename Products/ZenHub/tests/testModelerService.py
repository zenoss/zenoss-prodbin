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

from Products.ZenHub.services.ModelerService import ModelerService
import unittest

from Products.ZenTestCase.BaseTestCase import BaseTestCase

class TestModelerService(BaseTestCase):

    def setUp(self):
        BaseTestCase.setUp(self)
        devices = self.dmd.Devices
        devices.createOrganizer("Server")
        devices.createOrganizer("Network")

        dev = self.dmd.Devices.Server.createInstance("localhost")
        dev.setPerformanceMonitor('localhost')
        dev.zCollectorPlugins = ['zenoss.snmp.HRSWRunMap']

        dev2 = self.dmd.Devices.Network.createInstance("router")
        dev2.setPerformanceMonitor('localhost')
        dev2.zCollectorPlugins = ['zenoss.snmp.InterfaceMap']

    def test1(self):
        self.assertTrue(self.dmd)
        m = ModelerService(self.dmd, 'localhost')
        servers = m.remote_getDeviceListByOrganizer('Server')
        self.assertTrue(servers==['localhost'])
        mylist = m.remote_getDeviceListByMonitor('localhost')
        self.assert_('router' in mylist)
        self.assert_('localhost' in mylist)

    def testDeviceProxy(self):
        self.assertTrue(self.dmd)
        m = ModelerService(self.dmd, 'localhost')
        server = m.remote_getDeviceConfig(['localhost'])
        self.assertTrue(len(server) == 1)
        server = server[0]
        self.assertTrue(server.manageIp == '127.0.0.1')
        self.assertTrue(server.zSnmpVer)
        self.assertTrue(server.getSnmpStatusNumber() == 0)
        self.assertTrue(len(server.plugins) == 1)
        self.assertTrue(server.plugins[0].create().name() ==
                        'zenoss.snmp.HRSWRunMap')

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestModelerService))
    return suite
